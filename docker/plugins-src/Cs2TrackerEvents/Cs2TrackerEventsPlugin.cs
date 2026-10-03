using System.Collections.Concurrent;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Threading;
using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;
using CounterStrikeSharp.API.Modules.Entities.Constants;
using CounterStrikeSharp.API.Modules.Utils;

namespace Cs2TrackerEvents; int x = ;

/// <summary>
/// Captura a partida direto dos hooks e das structs server-side do
/// CounterStrikeSharp e escreve num arquivo JSONL, contornando o bug de
/// eventos faltando na demo gravada via GOTV/tv_record (ver
/// server-configs/cfg/gamemode_competitive_server.cfg e o histórico de
/// investigação no repo). Um evento por linha, sempre em append —
/// resistente a crash no meio da partida.
///
/// Arquivo sempre em &lt;game/csgo&gt;/events-live/current.jsonl. Truncado a
/// cada OnMapStart; o watcher.py (Python) lê e arquiva esse arquivo
/// assim que detecta o fim do mapa (mesmo sinal que já usa pro CSV de
/// stats da MatchZy — WritePlayerStatsToCsv).
///
/// Só conta rounds "ao vivo" (fora do warmup) via
/// GameRules().WarmupPeriod — rounds de warmup não viram round_num.
///
/// ------------------------------------------------------------------
/// DESENHO (v0.3.0) — três fontes, cada dado no lugar mais barato:
///
/// 1. EVENTO, quando o dado pertence a um instante. player_death carrega
///    a POSIÇÃO do matador e da vítima: é o tique exato, de graça, e
///    evita ter que casar a kill com uma amostra vizinha depois.
/// 2. FIM DE ROUND, quando o jogo já contou pra gente. CSMatchStats_t tem
///    entry, clutch 1v1/1v2, multi-kill, tiros dados/acertados, utility e
///    economia — tudo acumulado na partida. Emitimos o acumulado a cada
///    round e o Python tira a diferença. Não precisa derivar na mão o que
///    o engine já contou.
/// 3. AMOSTRAGEM POR TIQUE, só pro que é contínuo de verdade: o trajeto.
///    Como as kills trazem posição própria, a amostragem virou 2 Hz (era
///    8 Hz): serve pra mapa de calor de movimentação, não pra casar com
///    evento.
///
/// A v0.2.0-spike fazia o contrário — um loop de tique gordo com dinheiro,
/// flash e armadura por jogador 8x/s, reconstruindo no Python o que as
/// structs já entregam prontas.
/// </summary>
public class Cs2TrackerEventsPlugin : BasePlugin
{
    public override string ModuleName => "CS2 Tracker Events";
    public override string ModuleVersion => "0.4.0";
    public override string ModuleAuthor => "cs2-tracker";

    // 2 Hz. Numa partida de 30 min com 10 jogadores dá ~36 mil amostras de
    // jogador — contra ~144 mil a 8 Hz. O que se perde é resolução de
    // trajeto; o que interessa de precisão (onde matei, onde morri) agora
    // vem carimbado no próprio player_death.
    private const int SampleEveryTicks = 32;
    // Loga o custo médio/máximo do handler a cada ~10s.
    private const int CostReportEveryTicks = 64 * 10;
    // Teto da fila de escrita. A 2 Hz com 10 jogadores, 20 mil linhas são
    // mais de duas horas de folga — só enche se o disco parar de verdade,
    // e aí é melhor perder trajeto do que estourar memória.
    private const int FilaMaxLinhas = 20000;

    private string _eventsPath = "";
    private readonly object _writeLock = new();
    private int _roundNum = 0;

    private int _tickCounter = 0;
    private long _sampleTicks = 0;
    private double _costTotalMs = 0;
    private double _costMaxMs = 0;
    private double _costColetaMs = 0;
    private double _costEscritaMs = 0;
    private int _samples = 0;

    public override void Load(bool hotReload)
    {
        // Server.GameDirectory retorna .../game (não .../game/csgo, como o
        // nome sugeriria) — confirmado ao vivo via log de debug. O mount
        // do docker-compose.yml é em game/csgo/events-live, igual
        // demos-live/stats-live da MatchZy.
        _eventsPath = Path.Combine(Server.GameDirectory, "csgo", "events-live", "current.jsonl");
        RegisterListener<Listeners.OnMapStart>(OnMapStart);

        RegisterEventHandler<EventRoundStart>(OnRoundStart);
        RegisterEventHandler<EventRoundFreezeEnd>(OnRoundFreezeEnd);
        RegisterEventHandler<EventRoundEnd>(OnRoundEnd);
        RegisterEventHandler<EventRoundOfficiallyEnded>(OnRoundOfficiallyEnded);
        RegisterEventHandler<EventPlayerDeath>(OnPlayerDeath);
        RegisterEventHandler<EventPlayerHurt>(OnPlayerHurt);
        RegisterEventHandler<EventPlayerBlind>(OnPlayerBlind);
        RegisterEventHandler<EventBombPlanted>(OnBombPlanted);
        RegisterEventHandler<EventBombDefused>(OnBombDefused);
        RegisterListener<Listeners.OnTick>(OnTick);

        _pararEscrita = false;
        _threadEscrita = new Thread(LacoDeEscrita)
        {
            IsBackground = true,   // não segura o processo se o servidor cair
            Name = "Cs2TrackerEvents-escrita",
        };
        _threadEscrita.Start();

        // Sempre inicializa aqui, não só em hotReload — OnMapStart não
        // dispara pro mapa que já está carregado no momento em que o
        // plugin é carregado pela primeira vez (boot do servidor), então
        // sem isso o arquivo nunca chega a existir na primeira partida.
        ResetForNewMap();
    }

    private void OnMapStart(string mapName) => ResetForNewMap();

    private void ResetForNewMap()
    {
        _roundNum = 0;
        // A entidade de gamerules é recriada a cada mapa — segurar a antiga
        // daria leitura de warmup de um mapa que não existe mais.
        _rules = null;
        _tickCounter = 0;
        try
        {
            // Drena antes de truncar: linha do mapa anterior ainda na fila
            // apareceria no arquivo do mapa novo. Depois fecha, porque o
            // handle antigo aponta pro arquivo anterior (que o watcher.py
            // pode já ter renomeado) e escreveria nele.
            DrenaFila();
            CloseWriter();
            _filaCheiaAvisada = false;
            var dir = Path.GetDirectoryName(_eventsPath);
            if (dir != null) Directory.CreateDirectory(dir);
            // Trunca — o watcher.py já deve ter arquivado o arquivo do mapa
            // anterior antes do próximo OnMapStart disparar (mesma margem de
            // tempo que o resto do pipeline já assume pra ler demo/CSV).
            File.WriteAllText(_eventsPath, "");
            Server.PrintToConsole($"[Cs2TrackerEvents] Pronto — gravando em {_eventsPath}");
        }
        catch (Exception exc)
        {
            Server.PrintToConsole($"[Cs2TrackerEvents] ResetForNewMap FALHOU: {exc}");
        }
    }

    // Referência do GameRules, resolvida uma vez por mapa. A busca por
    // entidade custa ~0,14 ms de média e chega a 1,7 ms — irrelevante num
    // handler de evento (raro), caro no loop de amostragem. Medido no
    // spike de 22/09/2026.
    private CCSGameRules? _rules;

    private CCSGameRules? Rules()
    {
        if (_rules != null) return _rules;
        var proxy = Utilities.FindAllEntitiesByDesignerName<CCSGameRulesProxy>("cs_gamerules").FirstOrDefault();
        _rules = proxy?.GameRules;
        return _rules;
    }

    private bool IsLive()
    {
        var rules = Rules();
        return rules != null && !rules.WarmupPeriod;
    }

    private static string SideOf(CCSPlayerController? player)
    {
        if (player == null) return "";
        return player.Team switch
        {
            CsTeam.Terrorist => "t",
            CsTeam.CounterTerrorist => "ct",
            _ => "",
        };
    }

    private static string NameOf(CCSPlayerController? player) => player?.PlayerName ?? "";

    private static string? SteamIdOf(CCSPlayerController? player)
    {
        if (player == null || player.IsBot) return null;
        return player.SteamID.ToString();
    }

    /// <summary>
    /// x/y/z/callout de um jogador no instante da chamada, ou null se ele
    /// não tem pawn válido (desconectado, ainda não spawnou). Sai como
    /// objeto aninhado pra deixar explícito no JSONL que a posição pode
    /// faltar, em vez de gravar 0,0,0 e fingir que é o canto do mapa.
    /// </summary>
    private static object? PosOf(CCSPlayerController? player)
    {
        var pawn = player?.PlayerPawn?.Value;
        if (pawn == null || !pawn.IsValid) return null;
        var pos = pawn.AbsOrigin;
        if (pos == null) return null;
        return new
        {
            x = Math.Round(pos.X, 1),
            y = Math.Round(pos.Y, 1),
            z = Math.Round(pos.Z, 1),
            place = pawn.LastPlaceName,
        };
    }

    private static string ReasonToString(int reason) => (RoundEndReason)(uint)reason switch
    {
        RoundEndReason.TargetBombed => "bomb_exploded",
        RoundEndReason.BombDefused => "bomb_defused",
        RoundEndReason.CTsWin => "t_killed",
        RoundEndReason.TerroristsWin => "ct_killed",
        RoundEndReason.RoundDraw => "round_draw",
        RoundEndReason.TerroristsSurrender => "terrorists_surrender",
        RoundEndReason.CTsSurrender => "cts_surrender",
        var r => r.ToString(),
    };

    /// <summary>
    /// Escreve uma linha JSON no arquivo de eventos.
    ///
    /// Usa um StreamWriter mantido ABERTO. A versão anterior chamava
    /// File.AppendAllText, que abre, escreve e fecha a cada linha — e o
    /// arquivo mora num bind mount do Docker pro sistema de arquivos do
    /// Windows, onde abrir/fechar custa caro. Medido ao vivo em 23/09/2026:
    /// 12,4 ms de média por amostra, pico de 118 ms, contra os 15,6 ms de
    /// orçamento de um tique inteiro.
    ///
    /// `flush` é true pros eventos (raros, e não dá pra perder uma kill num
    /// crash) e false pro snapshot, que é 2x por segundo e cujo atraso não
    /// custa nada — esse é liberado em lote por FlushEveryNSamples.
    /// </summary>
    /// <summary>
    /// Serializa e ENFILEIRA. Quem grava em disco é uma thread própria.
    ///
    /// O arquivo mora num bind mount do Docker pro sistema de arquivos do
    /// Windows, e a gravação lá não só é lenta como PIORA conforme o arquivo
    /// cresce. Medido numa partida real em 23/09/2026, com o StreamWriter já
    /// mantido aberto:
    ///
    ///     início da partida:  escrita 0,881 ms
    ///     18 minutos depois:  escrita 8,222 ms, pico 99,9 ms
    ///
    /// A leitura das entidades ficou em 0,05–0,14 ms o tempo todo — o custo
    /// é todo I/O. Com 15,6 ms de orçamento por tique, isso derrubou o
    /// jogador com NETWORK_DISCONNECT_OVERFLOW no meio da partida.
    ///
    /// Nenhuma política de flush resolve isso na thread do jogo: o problema
    /// é o write em si. A única saída é a thread principal nunca esperar o
    /// disco. Aqui ela paga só serialização e um enfileiramento.
    /// </summary>
    private void Write(object payload)
    {
        try
        {
            if (_fila.Count >= FilaMaxLinhas)
            {
                // Disco travado. Descarta em vez de crescer sem limite — e
                // avisa uma vez só, porque isso pode disparar 2x por segundo.
                if (!_filaCheiaAvisada)
                {
                    _filaCheiaAvisada = true;
                    Server.PrintToConsole(
                        $"[Cs2TrackerEvents] fila cheia ({FilaMaxLinhas}) — descartando linhas. " +
                        "O disco não está acompanhando.");
                }
                return;
            }
            _fila.Enqueue(JsonSerializer.Serialize(payload));
        }
        catch (Exception exc)
        {
            Server.PrintToConsole($"[Cs2TrackerEvents] Falha ao serializar evento: {exc.Message}");
        }
    }

    private readonly ConcurrentQueue<string> _fila = new();
    private Thread? _threadEscrita;
    private volatile bool _pararEscrita;
    private bool _filaCheiaAvisada;
    private StreamWriter? _writer;

    /// <summary>
    /// Laço da thread de escrita: drena a fila, grava e libera. Se o disco
    /// engasgar, quem espera é ela — o servidor segue simulando.
    /// </summary>
    private void LacoDeEscrita()
    {
        while (!_pararEscrita)
        {
            if (!DrenaFila()) Thread.Sleep(50);
        }
        DrenaFila();   // saída limpa: não deixa linha na fila
    }

    /// <returns>true se escreveu alguma coisa.</returns>
    private bool DrenaFila()
    {
        if (_fila.IsEmpty) return false;
        lock (_writeLock)
        {
            try
            {
                var writer = Writer();
                if (writer == null) return false;
                var escreveu = false;
                while (_fila.TryDequeue(out var linha))
                {
                    writer.Write(linha);
                    writer.Write('\n');
                    escreveu = true;
                }
                if (escreveu) writer.Flush();
                return escreveu;
            }
            catch (Exception exc)
            {
                Server.PrintToConsole($"[Cs2TrackerEvents] Falha ao gravar: {exc.Message}");
                CloseWriter();   // handle provavelmente inválido; reabre na próxima
                return false;
            }
        }
    }

    private StreamWriter? Writer()
    {
        // O watcher.py renomeia current.jsonl no fim do mapa. Num handle já
        // aberto o rename é transparente (o inode acompanha), e as linhas do
        // mapa seguinte iriam parar dentro do arquivo arquivado. O stat que
        // detecta isso roda aqui, na thread de escrita, uma vez por lote —
        // nunca na thread do jogo.
        if (_writer != null && File.Exists(_eventsPath)) return _writer;
        CloseWriter();
        var dir = Path.GetDirectoryName(_eventsPath);
        if (dir != null) Directory.CreateDirectory(dir);
        _writer = new StreamWriter(_eventsPath, append: true, encoding: new UTF8Encoding(false));
        return _writer;
    }

    private void CloseWriter()
    {
        try { _writer?.Flush(); _writer?.Dispose(); }
        catch (Exception) { /* fechando mesmo assim */ }
        _writer = null;
    }

    // ------------------------------------------------------------------
    // Amostragem de trajeto
    // ------------------------------------------------------------------

    /// <summary>
    /// Uma linha "snapshot" por amostra, com TODOS os jogadores dentro —
    /// não uma linha por jogador. As chaves são curtas de propósito: são
    /// dezenas de milhares de registros por partida, e nome de campo longo
    /// aqui custa megabytes.
    ///
    /// Só trajeto: posição, vida e lado. Dinheiro, flash e armadura saíram
    /// daqui na v0.3.0 — vêm em freeze_end/round_stats, uma vez por round,
    /// direto das structs do jogo.
    /// </summary>
    private void OnTick()
    {
        if (_roundNum == 0) return;
        if (++_tickCounter % SampleEveryTicks != 0) return;

        var inicio = System.Diagnostics.Stopwatch.GetTimestamp();
        try
        {
            if (!IsLive()) return;

            var jogadores = new List<object>();
            foreach (var p in Utilities.GetPlayers())
            {
                if (p == null || !p.IsValid) continue;
                var pawn = p.PlayerPawn?.Value;
                if (pawn == null || !pawn.IsValid) continue;
                var pos = pawn.AbsOrigin;
                if (pos == null) continue;

                jogadores.Add(new
                {
                    n = p.PlayerName,
                    b = p.IsBot,
                    s = SideOf(p),
                    x = Math.Round(pos.X, 1),
                    y = Math.Round(pos.Y, 1),
                    z = Math.Round(pos.Z, 1),
                    h = pawn.Health,
                    p_ = pawn.LastPlaceName,
                });
            }
            if (jogadores.Count == 0) return;

            // Divide o custo em LEITURA (percorrer jogadores e puxar campos
            // do lado nativo) e ESCRITA (serializar + gravar). Sem isso, o
            // número agregado não diz qual dos dois otimizar — foi o que me
            // fez estimar errado na primeira vez.
            _costColetaMs += (System.Diagnostics.Stopwatch.GetTimestamp() - inicio)
                             * 1000.0 / System.Diagnostics.Stopwatch.Frequency;
            var tEscrita = System.Diagnostics.Stopwatch.GetTimestamp();

            // flush: false — snapshot é 2x por segundo e perder as últimas
            // amostras num crash não custa nada. Liberado em lote abaixo.
            Write(new
            {
                type = "snapshot",
                round_num = _roundNum,
                tick = Server.TickCount,
                players = jogadores,
            });
            _samples++;

            _costEscritaMs += (System.Diagnostics.Stopwatch.GetTimestamp() - tEscrita)
                              * 1000.0 / System.Diagnostics.Stopwatch.Frequency;
        }
        catch (Exception exc)
        {
            // Um erro aqui roda 2x por segundo — logar toda vez afogaria o
            // console. Loga uma vez e desliga a amostragem pro resto do mapa.
            Server.PrintToConsole($"[Cs2TrackerEvents] snapshot FALHOU, amostragem desligada: {exc.Message}");
            _roundNum = 0;
        }
        finally
        {
            var ms = (System.Diagnostics.Stopwatch.GetTimestamp() - inicio)
                     * 1000.0 / System.Diagnostics.Stopwatch.Frequency;
            _costTotalMs += ms;
            if (ms > _costMaxMs) _costMaxMs = ms;
            _sampleTicks++;

            if (_tickCounter % CostReportEveryTicks == 0 && _sampleTicks > 0)
            {
                // 1 tique = 15,6 ms de orçamento. Se a média passar de ~1 ms
                // a amostragem está cara demais e precisa de downsample.
                Server.PrintToConsole(
                    $"[Cs2TrackerEvents] custo snapshot: media {_costTotalMs / _sampleTicks:F3} ms, " +
                    $"max {_costMaxMs:F3} ms, {_samples} amostras " +
                    $"(leitura {_costColetaMs / _sampleTicks:F3} ms, " +
                    $"escrita {_costEscritaMs / _sampleTicks:F3} ms)");
                _costTotalMs = 0; _costMaxMs = 0; _sampleTicks = 0;
                _costColetaMs = 0; _costEscritaMs = 0;
            }
        }
    }

    // ------------------------------------------------------------------
    private HookResult OnRoundStart(EventRoundStart @event, GameEventInfo info)
    {
        if (!IsLive()) return HookResult.Continue;
        _roundNum++;
        Write(new
        {
            type = "round_start",
            round_num = _roundNum,
            tick = Server.TickCount,
            // O único jogador não-bot é o humano (design do projeto:
            // sempre 1 humano vs bots) — sem isso não tem como saber o
            // lado dele num round sem kill/morte/dano (a maioria).
            human_side = SideOf(Utilities.GetPlayers().FirstOrDefault(p => p.IsValid && !p.IsBot)),
        });
        return HookResult.Continue;
    }

    /// <summary>
    /// Fim do freezetime: é o instante canônico do "o que cada um comprou".
    /// Depois disso o valor de equipamento só cai (morre, dropa, gasta).
    /// É o que alimenta a classificação eco/force/full-buy.
    /// </summary>
    private HookResult OnRoundFreezeEnd(EventRoundFreezeEnd @event, GameEventInfo info)
    {
        if (_roundNum == 0 || !IsLive()) return HookResult.Continue;

        var jogadores = new List<object>();
        foreach (var p in Utilities.GetPlayers())
        {
            if (p == null || !p.IsValid) continue;
            var pawn = p.PlayerPawn?.Value;
            jogadores.Add(new
            {
                name = p.PlayerName,
                is_bot = p.IsBot,
                side = SideOf(p),
                // Os dois valores porque a hora exata em que o jogo grava
                // FreezetimeEndEquipmentValue relativa a ESTE evento não é
                // documentada; RoundStartEquipmentValue é o fallback óbvio.
                // O Python escolhe, e assim não precisa de outro teste ao
                // vivo só pra descobrir qual dos dois vem preenchido.
                equip_freeze_end = pawn?.FreezetimeEndEquipmentValue,
                equip_round_start = pawn?.RoundStartEquipmentValue,
                armor = p.PawnArmor,
                has_helmet = p.PawnHasHelmet,
                has_defuser = p.PawnHasDefuser,
                money = p.InGameMoneyServices?.Account,
            });
        }

        Write(new
        {
            type = "freeze_end",
            round_num = _roundNum,
            tick = Server.TickCount,
            players = jogadores,
        });
        return HookResult.Continue;
    }

    private HookResult OnRoundEnd(EventRoundEnd @event, GameEventInfo info)
    {
        if (_roundNum == 0 || !IsLive()) return HookResult.Continue;
        Write(new
        {
            type = "round_end",
            round_num = _roundNum,
            tick = Server.TickCount,
            winner = @event.Winner == (int)CsTeam.Terrorist ? "t"
                   : @event.Winner == (int)CsTeam.CounterTerrorist ? "ct" : "",
            reason = ReasonToString(@event.Reason),
        });
        return HookResult.Continue;
    }

    /// <summary>
    /// Despeja CSMatchStats_t de cada jogador. Os campos são ACUMULADOS na
    /// partida, não do round — emitir o acumulado a cada round deixa o
    /// Python tirar a diferença e ganhar o valor por round de brinde, e
    /// ainda sobrevive a round perdido (o acumulado se auto-corrige).
    ///
    /// É aqui que entram entry, clutch, multi-kill, precisão e utility: o
    /// engine já contou tudo isso, e a contagem dele é a verdade — a nossa
    /// derivação por janela de tique em stats.py é aproximação.
    /// </summary>
    private HookResult OnRoundOfficiallyEnded(EventRoundOfficiallyEnded @event, GameEventInfo info)
    {
        if (_roundNum == 0 || !IsLive()) return HookResult.Continue;

        var jogadores = new List<object>();
        foreach (var p in Utilities.GetPlayers())
        {
            if (p == null || !p.IsValid) continue;
            var ms = p.ActionTrackingServices?.MatchStats;
            if (ms == null) continue;

            jogadores.Add(new
            {
                name = p.PlayerName,
                is_bot = p.IsBot,
                side = SideOf(p),

                kills = ms.Kills,
                deaths = ms.Deaths,
                assists = ms.Assists,
                damage = ms.Damage,
                headshot_kills = ms.HeadShotKills,
                objective = ms.Objective,
                live_time = ms.LiveTime,

                // Precisão real — era Nível 2 no relatório (dem.shots) e
                // nunca foi lida de lugar nenhum.
                shots_fired = ms.ShotsFiredTotal,
                shots_on_target = ms.ShotsOnTargetTotal,

                entry_count = ms.EntryCount,
                entry_wins = ms.EntryWins,
                clutch_1v1_count = ms.I1v1Count,
                clutch_1v1_wins = ms.I1v1Wins,
                clutch_1v2_count = ms.I1v2Count,
                clutch_1v2_wins = ms.I1v2Wins,
                multi_2k = ms.Enemy2Ks,
                multi_3k = ms.Enemy3Ks,
                multi_4k = ms.Enemy4Ks,
                multi_5k = ms.Enemy5Ks,

                utility_count = ms.Utility_Count,
                utility_successes = ms.Utility_Successes,
                utility_enemies = ms.Utility_Enemies,
                utility_damage = ms.UtilityDamage,
                flash_count = ms.Flash_Count,
                flash_successes = ms.Flash_Successes,
                enemies_flashed = ms.EnemiesFlashed,

                equipment_value = ms.EquipmentValue,
                money_saved = ms.MoneySaved,
                cash_earned = ms.CashEarned,
                kill_reward = ms.KillReward,
                // Dinheiro de verdade — o awpy não expõe em versão nenhuma;
                // era a limitação registrada no topo do parser.py.
                money = p.InGameMoneyServices?.Account,
                cash_spent_round = p.InGameMoneyServices?.CashSpentThisRound,
            });
        }

        Write(new
        {
            type = "round_stats",
            round_num = _roundNum,
            tick = Server.TickCount,
            players = jogadores,
        });

        Write(new
        {
            type = "round_officially_ended",
            round_num = _roundNum,
            tick = Server.TickCount,
        });
        return HookResult.Continue;
    }

    private HookResult OnPlayerDeath(EventPlayerDeath @event, GameEventInfo info)
    {
        if (_roundNum == 0 || !IsLive()) return HookResult.Continue;
        Write(new
        {
            type = "player_death",
            round_num = _roundNum,
            tick = Server.TickCount,
            attacker_name = NameOf(@event.Attacker),
            attacker_steamid = SteamIdOf(@event.Attacker),
            attacker_side = SideOf(@event.Attacker),
            victim_name = NameOf(@event.Userid),
            victim_steamid = SteamIdOf(@event.Userid),
            victim_side = SideOf(@event.Userid),
            weapon = @event.Weapon,
            headshot = @event.Headshot,
            distance = @event.Distance,
            // Posição no instante exato da kill. É o que o heatmap quer, e
            // vindo daqui não precisa casar a kill com uma amostra vizinha
            // do snapshot (que só existe a cada 32 tiques).
            attacker_pos = PosOf(@event.Attacker),
            victim_pos = PosOf(@event.Userid),
        });
        return HookResult.Continue;
    }

    private HookResult OnPlayerHurt(EventPlayerHurt @event, GameEventInfo info)
    {
        if (_roundNum == 0 || !IsLive()) return HookResult.Continue;
        Write(new
        {
            type = "player_hurt",
            round_num = _roundNum,
            tick = Server.TickCount,
            attacker_name = NameOf(@event.Attacker),
            attacker_steamid = SteamIdOf(@event.Attacker),
            victim_name = NameOf(@event.Userid),
            victim_steamid = SteamIdOf(@event.Userid),
            weapon = @event.Weapon,
            hitgroup = @event.Hitgroup,
            dmg_health = @event.DmgHealth,
            dmg_armor = @event.DmgArmor,
        });
        return HookResult.Continue;
    }

    /// <summary>
    /// Tempo cego SOFRIDO. CSMatchStats_t conta os flashes que você acertou
    /// (Flash_Count/Successes/EnemiesFlashed) mas não os que acertaram você
    /// — esse lado só existe aqui.
    /// </summary>
    private HookResult OnPlayerBlind(EventPlayerBlind @event, GameEventInfo info)
    {
        if (_roundNum == 0 || !IsLive()) return HookResult.Continue;
        Write(new
        {
            type = "player_blind",
            round_num = _roundNum,
            tick = Server.TickCount,
            attacker_name = NameOf(@event.Attacker),
            attacker_side = SideOf(@event.Attacker),
            victim_name = NameOf(@event.Userid),
            victim_side = SideOf(@event.Userid),
            duration = Math.Round(@event.BlindDuration, 2),
        });
        return HookResult.Continue;
    }

    private HookResult OnBombPlanted(EventBombPlanted @event, GameEventInfo info)
    {
        if (_roundNum == 0 || !IsLive()) return HookResult.Continue;
        Write(new
        {
            type = "bomb_planted",
            round_num = _roundNum,
            tick = Server.TickCount,
            player_name = NameOf(@event.Userid),
            steamid = SteamIdOf(@event.Userid),
            // @event.Site é o ÍNDICE DE ENTIDADE do alvo da bomba (valores
            // observados: 370, 3956), não 0/1 — e o parser.py assumia 0=A,
            // 1=B, então gravava NULL em todos os 266 rounds de origem
            // 'events'. place é o nome que o jogo dá à região ("BombsiteA"),
            // que é o que dá pra normalizar de verdade. site fica junto só
            // pra não perder o dado bruto.
            site = @event.Site,
            place = @event.Userid?.PlayerPawn?.Value?.LastPlaceName,
        });
        return HookResult.Continue;
    }

    private HookResult OnBombDefused(EventBombDefused @event, GameEventInfo info)
    {
        if (_roundNum == 0 || !IsLive()) return HookResult.Continue;
        Write(new
        {
            type = "bomb_defused",
            round_num = _roundNum,
            tick = Server.TickCount,
            player_name = NameOf(@event.Userid),
            steamid = SteamIdOf(@event.Userid),
            site = @event.Site,
            place = @event.Userid?.PlayerPawn?.Value?.LastPlaceName,
        });
        return HookResult.Continue;
    }

    /// <summary>
    /// Para a thread de escrita e garante que o que estava na fila foi pro
    /// disco. Sem isso, um recarregamento de plugin no fim da partida perderia
    /// os últimos rounds.
    /// </summary>
    public override void Unload(bool hotReload)
    {
        _pararEscrita = true;
        try { _threadEscrita?.Join(3000); }
        catch (Exception) { /* saindo de qualquer jeito */ }
        DrenaFila();
        CloseWriter();
    }
}
