"""Jobs EnglishWordBook 原生桌面界面。"""
# JOBS_TERMINAL_STYLE_GUARD_V1_BEGIN
# 保存与恢复由监督进程负责；导入本模块时不接管终端。
def _jobs_terminal_style_bootstrap_v1():
    import os as _os
    import base64 as _base64
    import json as _json
    import shutil as _shutil
    import subprocess as _subprocess
    import sys as _sys
    import tempfile as _tempfile

    _entry = _os.path.abspath(__file__)
    if _os.environ.get("JOBS_TERMINAL_STYLE_REEXEC") == _entry:
        _os.environ.pop("JOBS_TERMINAL_STYLE_REEXEC", None)
        return
    if (getattr(_sys, "frozen", False) or not _sys.stdin or not _sys.stdout
            or not _sys.stdin.isatty() or not _sys.stdout.isatty()
            or "NO_COLOR" in _os.environ
            or _os.environ.get("PLAIN_OUTPUT") == "1"
            or _os.environ.get("IS_SOURCETREE_RUNTIME") == "1"
            or any(_key.upper().startswith(("SOURCETREE", "SOURCE_TREE"))
                   for _key in _os.environ)):
        return
    if _os.name != "nt" and (_os.environ.get("TERM", "") in ("", "dumb")
                             or _os.environ.get("TMUX") or _os.environ.get("STY")):
        return
    _original = getattr(_sys, "orig_argv", None)
    _module_start = False
    for _argument in list(_original[1:]) if _original else []:
        if _argument == "--" or _os.path.abspath(_argument) == _entry:
            break
        if _argument in ("-c", "-m"):
            _module_start = True
            break
    if _module_start:
        _os.environ.update(NO_COLOR="1", PLAIN_OUTPUT="1", FORCE_COLOR="0", CLICOLOR="0")
        return
    _command = [_sys.executable] + (list(_original[1:]) if _original else list(_sys.argv))
    _environment = _os.environ.copy()
    _environment["JOBS_TERMINAL_STYLE_REEXEC"] = _entry
    _shell_core = r"""# 临时保护当前终端配色，业务进程自行管理原有退出清理。
jobs_terminal_style_run() {
    # 无法可靠保存原色时，沿用脚本已有的纯文本约定。
    jobs_terminal_style_plain() {
        PLAIN_OUTPUT=1
        NO_COLOR=1
        FORCE_COLOR=0
        CLICOLOR=0
        ANSI_COLORS_DISABLED=1
        npm_config_color=false
        export PLAIN_OUTPUT NO_COLOR FORCE_COLOR CLICOLOR ANSI_COLORS_DISABLED npm_config_color
        if "$@"; then
            jobs_style_exit_status=0
        else
            jobs_style_exit_status=$?
        fi
        exit "$jobs_style_exit_status"
    }
    if [ ! -t 0 ] || [ ! -t 1 ] || [ -z "${TERM:-}" ] ||
       [ "${TERM:-}" = dumb ] || [ "${NO_COLOR+x}" = x ] ||
       [ "${PLAIN_OUTPUT:-0}" = 1 ] || [ "${IS_SOURCETREE_RUNTIME:-0}" = 1 ] ||
       env | LC_ALL=C grep -qiE '^(SOURCETREE|SOURCE_TREE)'; then
        if "$@"; then
            jobs_style_exit_status=0
        else
            jobs_style_exit_status=$?
        fi
        exit "$jobs_style_exit_status"
    fi
    if [ -n "${TMUX:-}${STY:-}" ]; then
        jobs_terminal_style_plain "$@"
    fi
    jobs_style_tty=$(tty 2>/dev/null) || jobs_terminal_style_plain "$@"
    if ! ps -o pgid= -o tpgid= -p "$$" 2>/dev/null |
         LC_ALL=C awk 'NF == 2 && $1 == $2 && $1 > 0 { foreground = 1 } END { exit !foreground }'; then
        jobs_terminal_style_plain "$@"
    fi
    case ${JOBS_TERMINAL_STYLE_OWNER:-} in
        ''|*[!0-9]*) ;;
        *)
            if [ "${JOBS_TERMINAL_STYLE_TTY:-}" = "$jobs_style_tty" ] &&
               kill -0 "$JOBS_TERMINAL_STYLE_OWNER" 2>/dev/null; then
                if "$@"; then
                    jobs_style_exit_status=0
                else
                    jobs_style_exit_status=$?
                fi
                exit "$jobs_style_exit_status"
            fi
            ;;
    esac
    jobs_style_stty=$(stty -g 2>/dev/null < /dev/tty) || jobs_terminal_style_plain "$@"
    jobs_style_saved=''
    jobs_style_saved_rows=''
    jobs_style_applied_rows=''
    jobs_style_changed=0
    jobs_style_applied_complete=0
    jobs_style_query_active=0
    jobs_style_recovery=''
    jobs_style_exit_status=0
    jobs_style_esc=$(printf '\033')
    jobs_style_bel=$(printf '\007')
    # 只接受本次请求对应的 RGB 响应；非协议输入使本次探测失败。
    jobs_terminal_style_query() {
        jobs_style_query_key=$1
        printf '\033]%s;?\007' "$jobs_style_query_key" > /dev/tty || return 1
        jobs_style_reply=''
        for jobs_style_attempt in 1 2 3; do
            jobs_style_piece=$(dd bs=256 count=1 2>/dev/null < /dev/tty)
            jobs_style_reply=$jobs_style_reply$jobs_style_piece
            case $jobs_style_reply in
                *"$jobs_style_bel"|*"$jobs_style_esc\\") break ;;
                '') ;;
                "$jobs_style_esc"*) ;;
                *) break ;;
            esac
        done
        case $jobs_style_reply in
            "$jobs_style_esc]$jobs_style_query_key;rgb:"*"$jobs_style_bel")
                jobs_style_rgb=${jobs_style_reply#"$jobs_style_esc]$jobs_style_query_key;rgb:"}
                jobs_style_rgb=${jobs_style_rgb%"$jobs_style_bel"}
                ;;
            "$jobs_style_esc]$jobs_style_query_key;rgb:"*"$jobs_style_esc\\")
                jobs_style_rgb=${jobs_style_reply#"$jobs_style_esc]$jobs_style_query_key;rgb:"}
                jobs_style_rgb=${jobs_style_rgb%"$jobs_style_esc\\"}
                ;;
            *) return 1 ;;
        esac
        jobs_style_normalized=$(printf '%s\n' "$jobs_style_rgb" | LC_ALL=C awk -F/ '
            NF != 3 { exit 1 }
            {
                for (i = 1; i <= 3; i++) {
                    h = tolower($i)
                    if (length(h) < 1 || length(h) > 4 || h ~ /[^0-9a-f]/) exit 1
                    n = 0
                    for (j = 1; j <= length(h); j++) n = n * 16 + index("0123456789abcdef", substr(h, j, 1)) - 1
                    value[i] = int(n * 65535 / (16 ^ length(h) - 1) + 0.5)
                }
                printf "%d/%d/%d", value[1], value[2], value[3]
            }
        ') || return 1
        [ -n "$jobs_style_normalized" ]
    }
    # 查询可用不代表终端允许改色，按目标值核对实际生效结果。
    jobs_terminal_style_accepts_target() {
        jobs_style_requested_hex=''
        case $1 in
            10|12) jobs_style_requested_hex=ffffff ;;
            11) jobs_style_requested_hex=000000 ;;
            '4;'*)
                jobs_style_requested_index=0
                for jobs_style_requested_color in 000000 ff5f56 5fd787 ffd75f 5fafff d787ff 5fd7ff eeeeee 9e9e9e ff8787 87ffaf ffff87 87bfff ffafff afffff ffffff; do
                    if [ "4;$jobs_style_requested_index" = "$1" ]; then
                        jobs_style_requested_hex=$jobs_style_requested_color
                        break
                    fi
                    jobs_style_requested_index=$((jobs_style_requested_index + 1))
                done
                ;;
        esac
        [ -n "$jobs_style_requested_hex" ] || return 1
        printf '%s|%s\n' "$jobs_style_normalized" "$jobs_style_requested_hex" | LC_ALL=C awk -F'|' '
            function hexbyte(h) {
                return (index("0123456789abcdef", substr(h, 1, 1)) - 1) * 16 + index("0123456789abcdef", substr(h, 2, 1)) - 1
            }
            {
                if (split($1, actual, "/") != 3 || length($2) != 6) exit 1
                for (i = 1; i <= 3; i++) {
                    difference = actual[i] - hexbyte(substr($2, i * 2 - 1, 2)) * 257
                    if (difference < -255 || difference > 255) exit 1
                }
            }
        '
    }
    # 检测到后续改色时只恢复仍由本次保护持有的项，保留独立恢复入口。
    jobs_terminal_style_cleanup() {
        jobs_style_result=$1
        trap '' HUP INT TERM
        if [ "$jobs_style_query_active" = 1 ]; then
            stty "$jobs_style_stty" 2>/dev/null < /dev/tty || :
            jobs_style_query_active=0
        fi
        if [ "$jobs_style_changed" = 1 ]; then
            jobs_style_cleanup_ok=0
            jobs_style_conflicts=''
            jobs_style_restore_safe=''
            if [ "$jobs_style_applied_complete" = 1 ]; then
                jobs_style_stty=$(stty -g 2>/dev/null < /dev/tty) || jobs_style_stty=''
                if [ -n "$jobs_style_stty" ] && stty -echo -icanon min 0 time 1 2>/dev/null < /dev/tty; then
                    jobs_style_query_active=1
                    jobs_style_cleanup_ok=1
                    while IFS='|' read -r jobs_style_key jobs_style_expected jobs_style_original; do
                        [ -n "$jobs_style_key" ] || continue
                        if ! jobs_terminal_style_query "$jobs_style_key"; then
                            jobs_style_cleanup_ok=0
                            break
                        fi
                        if [ "$jobs_style_normalized" = "$jobs_style_expected" ]; then
                            jobs_style_restore_safe=$jobs_style_restore_safe$jobs_style_original
                        else
                            jobs_style_conflicts="$jobs_style_conflicts $jobs_style_key"
                        fi
                    done <<JOBS_STYLE_APPLIED
$jobs_style_applied_rows
JOBS_STYLE_APPLIED
                    stty "$jobs_style_stty" 2>/dev/null < /dev/tty || jobs_style_cleanup_ok=0
                    jobs_style_query_active=0
                fi
            fi
            if [ "$jobs_style_cleanup_ok" = 1 ] && printf '%s\033[0m' "$jobs_style_restore_safe" > /dev/tty; then
                if [ -z "$jobs_style_conflicts" ]; then
                    rm -f "$jobs_style_recovery"
                    rmdir "${jobs_style_recovery%/*}" 2>/dev/null || :
                else
                    printf '检测到运行期间的配色变更，已保留这些项：%s\n' "$jobs_style_conflicts" >&2
                    printf '确认要覆盖后续改色时才使用恢复入口：sh "%s"\n' "$jobs_style_recovery" >&2
                    [ "$jobs_style_result" -ne 0 ] || jobs_style_result=1
                fi
            else
                printf '终端配色未能安全自动恢复；确认覆盖当前配色后可运行：sh "%s"\n' "$jobs_style_recovery" >&2
                [ "$jobs_style_result" -ne 0 ] || jobs_style_result=1
            fi
        fi
        if [ "${2:-}" = continue ]; then
            jobs_style_cleanup_status=$jobs_style_result
            return 0
        fi
        exit "$jobs_style_result"
    }
    trap 'jobs_terminal_style_cleanup "$jobs_style_exit_status"' 0
    trap 'jobs_style_exit_status=129; exit 129' HUP
    trap 'jobs_style_exit_status=130; exit 130' INT
    trap 'jobs_style_exit_status=143; exit 143' TERM
    if ! stty -echo -icanon min 0 time 1 2>/dev/null < /dev/tty; then
        jobs_terminal_style_plain "$@"
    fi
    jobs_style_query_active=1
    jobs_style_probe_ok=1
    for jobs_style_key in 10 11 12 '4;0' '4;1' '4;2' '4;3' '4;4' '4;5' '4;6' '4;7' '4;8' '4;9' '4;10' '4;11' '4;12' '4;13' '4;14' '4;15'; do
        if ! jobs_terminal_style_query "$jobs_style_key"; then
            jobs_style_probe_ok=0
            break
        fi
        jobs_style_saved=$jobs_style_saved$jobs_style_reply
        jobs_style_saved_rows="$jobs_style_saved_rows$jobs_style_key|$jobs_style_reply
"
    done
    stty "$jobs_style_stty" 2>/dev/null < /dev/tty || { jobs_style_exit_status=1; exit 1; }
    jobs_style_query_active=0
    if [ "$jobs_style_probe_ok" != 1 ]; then
        printf '%s\n' '终端不支持完整配色保存，或启动时收到其它输入；保留原配色并使用纯文本。' >&2
        jobs_terminal_style_plain "$@"
    fi
    jobs_style_recovery_dir=$(umask 077; mktemp -d "${TMPDIR:-/tmp}/jobs-terminal-style.XXXXXX") || jobs_terminal_style_plain "$@"
    jobs_style_recovery=$jobs_style_recovery_dir/restore.sh
    if ! (umask 077; {
        printf '#!/bin/sh\n'
        printf '[ -t 0 ] && [ "$(tty)" = '\''%s'\'' ] || { printf '\''请在原终端运行恢复入口。\\n'\'' >&2; exit 1; }\n' "$jobs_style_tty"
        printf 'printf '\''本操作会覆盖此终端当前配色。确认恢复脚本启动前的配色，请输入 YES：'\'' >&2\n'
        printf 'IFS= read -r jobs_restore_choice\n[ "$jobs_restore_choice" = YES ] || exit 1\n'
        printf 'printf '\''%%s\\033[0m'\'' '\''%s'\'' > /dev/tty\n' "$jobs_style_saved"
    } > "$jobs_style_recovery"); then
        printf '%s\n' '无法保存终端配色恢复入口；保留原配色并使用纯文本。' >&2
        jobs_terminal_style_plain "$@"
    fi
    printf '正在准备本次终端临时配色；强退后恢复入口：sh "%s"\n' "$jobs_style_recovery" >&2
    jobs_style_changed=1
    printf '\033]10;#ffffff\007\033]11;#000000\007\033]12;#ffffff\007' > /dev/tty
    jobs_style_index=0
    for jobs_style_color in 000000 ff5f56 5fd787 ffd75f 5fafff d787ff 5fd7ff eeeeee 9e9e9e ff8787 87ffaf ffff87 87bfff ffafff afffff ffffff; do
        printf '\033]4;%s;#%s\007' "$jobs_style_index" "$jobs_style_color" > /dev/tty
        jobs_style_index=$((jobs_style_index + 1))
    done
    printf '\033[0m' > /dev/tty
    jobs_style_stty=$(stty -g 2>/dev/null < /dev/tty) || { jobs_style_exit_status=1; exit 1; }
    stty -echo -icanon min 0 time 1 2>/dev/null < /dev/tty || { jobs_style_exit_status=1; exit 1; }
    jobs_style_query_active=1
    jobs_style_probe_ok=1
    jobs_style_targets_ok=1
    while IFS='|' read -r jobs_style_key jobs_style_original; do
        [ -n "$jobs_style_key" ] || continue
        if ! jobs_terminal_style_query "$jobs_style_key"; then
            jobs_style_probe_ok=0
            break
        fi
        jobs_style_applied_rows="$jobs_style_applied_rows$jobs_style_key|$jobs_style_normalized|$jobs_style_original
"
        if ! jobs_terminal_style_accepts_target "$jobs_style_key"; then
            jobs_style_targets_ok=0
        fi
    done <<JOBS_STYLE_ORIGINAL
$jobs_style_saved_rows
JOBS_STYLE_ORIGINAL
    stty "$jobs_style_stty" 2>/dev/null < /dev/tty || { jobs_style_exit_status=1; exit 1; }
    jobs_style_query_active=0
    if [ "$jobs_style_probe_ok" != 1 ]; then
        printf '%s\n' '无法核实本次临时配色，已停止启动业务。' >&2
        jobs_style_exit_status=1
        exit 1
    fi
    jobs_style_applied_complete=1
    if [ "$jobs_style_targets_ok" != 1 ]; then
        jobs_terminal_style_cleanup 0 continue
        jobs_style_changed=0
        if [ "$jobs_style_cleanup_status" != 0 ]; then
            jobs_style_exit_status=1
            exit 1
        fi
        trap 'jobs_style_exit_status=129; exit 129' HUP
        trap 'jobs_style_exit_status=130; exit 130' INT
        trap 'jobs_style_exit_status=143; exit 143' TERM
        printf '%s\n' '终端未接受本次配色，已恢复原配色并使用纯文本。' >&2
        jobs_terminal_style_plain "$@"
    fi
    printf '%s\n' '本次终端已临时使用黑底白字。' >&2
    JOBS_TERMINAL_STYLE_TTY=$jobs_style_tty
    JOBS_TERMINAL_STYLE_OWNER=$$
    export JOBS_TERMINAL_STYLE_TTY JOBS_TERMINAL_STYLE_OWNER
    if "$@"; then
        jobs_style_exit_status=0
    else
        jobs_style_exit_status=$?
    fi
    exit "$jobs_style_exit_status"
}
"""
    _powershell_core = r"""$__jobsTerminalCommand = @($args)
# BEGIN JOBS_TERMINAL_STYLE_V1 - session-only colors; no profile or registry changes.
function New-JobsTerminalStyleState {
    if ($PSVersionTable.PSVersion.Major -lt 5) { return @{ JobsTerminalPlainFallback = $true; Before = @{} } }
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT -or $Host.Name -ne 'ConsoleHost') { return $null }
    if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected -or [Console]::IsErrorRedirected) { return $null }
    if ((Test-Path Env:NO_COLOR) -or $env:TERM -ieq 'dumb' -or $env:PLAIN_OUTPUT -eq '1') { return $null }
    foreach ($key in [Environment]::GetEnvironmentVariables().Keys) {
        if ([string]$key -match '^(?i:SOURCE_?TREE)') { return $null }
    }
    if (-not ('Jobs.TerminalStyleV1.Native' -as [type])) {
        try {
        Add-Type -ErrorAction Stop -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
namespace Jobs.TerminalStyleV1 {
    public static class Native {
        [StructLayout(LayoutKind.Explicit, Size=20, CharSet=CharSet.Unicode)]
        public struct InputRecord {
            [FieldOffset(0)] public ushort Kind;
            [FieldOffset(4)] public int Down;
            [FieldOffset(8)] public ushort Repeat;
            [FieldOffset(10)] public ushort Key;
            [FieldOffset(12)] public ushort Scan;
            [FieldOffset(14)] public char Character;
            [FieldOffset(16)] public uint Modifiers;
        }
        [DllImport("kernel32.dll")] static extern IntPtr GetStdHandle(int n);
        [DllImport("kernel32.dll")] static extern IntPtr GetConsoleWindow();
        [DllImport("kernel32.dll")] static extern bool GetConsoleMode(IntPtr h, out uint mode);
        [DllImport("kernel32.dll")] static extern bool SetConsoleMode(IntPtr h, uint mode);
        [DllImport("kernel32.dll")] static extern uint WaitForSingleObject(IntPtr h, uint milliseconds);
        [DllImport("kernel32.dll")] static extern bool GetNumberOfConsoleInputEvents(IntPtr h, out uint count);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true)] static extern bool ReadConsoleInputW(IntPtr h, [Out] InputRecord[] records, uint count, out uint read);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, ExactSpelling=true)] static extern bool WriteConsoleInputW(IntPtr h, InputRecord[] records, uint count, out uint written);
        const string OwnerName = "JOBS_TERMINAL_STYLE_WINDOWS_OWNER";
        static readonly string[] Keys = { "10", "11", "4;0", "4;1", "4;2", "4;3", "4;4", "4;5", "4;6", "4;7", "4;8", "4;9", "4;10", "4;11", "4;12", "4;13", "4;14", "4;15" };
        static readonly string[] Hex = { "000000", "ff5f56", "5fd787", "ffd75f", "5fafff", "d787ff", "5fd7ff", "eeeeee", "9e9e9e", "ff8787", "87ffaf", "ffff87", "87bfff", "ffafff", "afffff", "ffffff" };
        static readonly Regex Reply = new Regex("\\x1b\\](?<key>10|11|4;[0-9]{1,2});(?<rgb>rgb:[0-9a-f]{1,4}/[0-9a-f]{1,4}/[0-9a-f]{1,4})(?:\\x07|\\x1b\\\\)", RegexOptions.IgnoreCase);
        public sealed class State {
            public IntPtr Input, Output;
            public uint OutputMode;
            public ConsoleColor Foreground, Background;
            public Dictionary<string,string> Original, Applied;
            public string Owner, PreviousOwner, Recovery;
            public bool Active, ModeChanged, Fallback;
            public Dictionary<string,string> EnvironmentBefore = new Dictionary<string,string>();
        }
        static string Escape(string key, string value) { return "\x1b]" + key + ";" + value + "\x07"; }
        static string Rgb(string hex) { return "rgb:" + hex.Substring(0,2) + "/" + hex.Substring(2,2) + "/" + hex.Substring(4,2); }
        static string Normal(string rgb) {
            string[] parts = rgb.Substring(4).Split('/');
            for (int n=0; n<3; n++) {
                int maximum = (1 << (4 * parts[n].Length)) - 1;
                int value = Convert.ToInt32(parts[n],16);
                parts[n] = ((value * 65535L + maximum/2) / maximum).ToString("x4");
            }
            return String.Join("/",parts);
        }
        // Preserve unrelated key/window records instead of consuming user input during color queries.
        static Dictionary<string,string> Query(State state) {
            uint pending;
            if (!GetNumberOfConsoleInputEvents(state.Input,out pending) || pending != 0) { return null; }
            StringBuilder commands = new StringBuilder();
            foreach (string key in Keys) { commands.Append(Escape(key,"?")); }
            Console.Write(commands.ToString());
            List<InputRecord> records = new List<InputRecord>();
            List<int> characterIndices = new List<int>();
            StringBuilder text = new StringBuilder();
            Dictionary<string,string> result = new Dictionary<string,string>();
            Stopwatch timer = Stopwatch.StartNew();
            try {
                while (timer.ElapsedMilliseconds < 600) {
                    if (result.Count == Keys.Length && GetNumberOfConsoleInputEvents(state.Input,out pending) && pending == 0) { break; }
                    if (WaitForSingleObject(state.Input,20) != 0) { continue; }
                    InputRecord[] item = new InputRecord[1]; uint read;
                    if (!ReadConsoleInputW(state.Input,item,1,out read) || read != 1) { break; }
                    int index = -1;
                    if (item[0].Kind == 1 && item[0].Character != '\0') {
                        if (item[0].Down != 0) { index = text.Length; text.Append(item[0].Character); }
                        else if (text.Length != 0 && text[text.Length-1] == item[0].Character) { index = text.Length-1; }
                    }
                    records.Add(item[0]); characterIndices.Add(index);
                    foreach (Match match in Reply.Matches(text.ToString())) {
                        string key = match.Groups["key"].Value;
                        if (Array.IndexOf(Keys,key) >= 0) { result[key] = match.Groups["rgb"].Value; }
                    }
                }
            } finally {
                bool[] used = new bool[text.Length];
                foreach (Match match in Reply.Matches(text.ToString())) {
                    for (int n=match.Index; n<match.Index+match.Length; n++) { used[n] = true; }
                }
                List<InputRecord> replay = new List<InputRecord>();
                for (int n=0; n<records.Count; n++) {
                    int index = characterIndices[n];
                    if (index < 0 || !used[index]) { replay.Add(records[n]); }
                }
                if (replay.Count != 0) {
                    uint written;
                    if (!WriteConsoleInputW(state.Input,replay.ToArray(),(uint)replay.Count,out written) || written != replay.Count) {
                        Console.Error.WriteLine("[Jobs] Could not replay terminal input; color protection is unavailable.");
                        result.Clear();
                    }
                }
            }
            return result.Count == Keys.Length ? result : null;
        }
        static void Plain(State state) {
            foreach (string key in new string[] { "NO_COLOR", "PLAIN_OUTPUT", "FORCE_COLOR", "CLICOLOR", "ANSI_COLORS_DISABLED" }) {
                state.EnvironmentBefore[key] = Environment.GetEnvironmentVariable(key);
                Environment.SetEnvironmentVariable(key, key == "FORCE_COLOR" || key == "CLICOLOR" ? "0" : "1");
            }
            state.Fallback = true;
        }
        public static void Enter(State state) {
            try {
                state.Input = GetStdHandle(-10); state.Output = GetStdHandle(-11);
                uint inputMode;
                if (!GetConsoleMode(state.Input,out inputMode) || !GetConsoleMode(state.Output,out state.OutputMode)) { Plain(state); return; }
                IntPtr window = GetConsoleWindow();
                if (window == IntPtr.Zero) { Plain(state); return; }
                string identity = window.ToInt64().ToString("x");
                state.PreviousOwner = Environment.GetEnvironmentVariable(OwnerName);
                if (!String.IsNullOrEmpty(state.PreviousOwner)) {
                    string[] owner = state.PreviousOwner.Split(':');
                    int pid; long started;
                    if (owner.Length == 3 && owner[0] == identity && Int32.TryParse(owner[1],out pid) && Int64.TryParse(owner[2],out started)) {
                        try { if (Process.GetProcessById(pid).StartTime.ToUniversalTime().Ticks == started) { return; } } catch {}
                    }
                }
                state.Foreground = Console.ForegroundColor; state.Background = Console.BackgroundColor;
                if ((state.OutputMode & 4) == 0) {
                    if (!SetConsoleMode(state.Output,state.OutputMode | 4)) { Plain(state); return; }
                    state.ModeChanged = true;
                }
                state.Original = Query(state);
                if (state.Original == null) { Restore(state); Plain(state); return; }
                state.Applied = new Dictionary<string,string>();
                state.Applied["10"] = "rgb:ff/ff/ff"; state.Applied["11"] = "rgb:00/00/00";
                for (int n=0; n<16; n++) { state.Applied["4;"+n] = Rgb(Hex[n]); }
                StringBuilder restore = new StringBuilder();
                foreach (string key in Keys) { restore.Append(Escape(key,state.Original[key])); }
                string encoded = Convert.ToBase64String(Encoding.UTF8.GetBytes(restore.ToString()));
                state.Recovery = Path.Combine(Path.GetTempPath(),"JobsTerminalStyle-"+Process.GetCurrentProcess().Id+"-"+Guid.NewGuid().ToString("N")+".ps1");
                string manual = "# Restore only the session colors saved by this Jobs script.\r\n"+
                    "if ([Console]::IsOutputRedirected) { throw 'Run in the original console.' }\r\n"+
                    "Add-Type -Namespace Jobs -Name RecoveryConsole -MemberDefinition '[System.Runtime.InteropServices.DllImport(\"kernel32.dll\")] public static extern System.IntPtr GetStdHandle(int n); [System.Runtime.InteropServices.DllImport(\"kernel32.dll\")] public static extern bool GetConsoleMode(System.IntPtr h, out uint m); [System.Runtime.InteropServices.DllImport(\"kernel32.dll\")] public static extern bool SetConsoleMode(System.IntPtr h, uint m);'\r\n"+
                    "$h = [Jobs.RecoveryConsole]::GetStdHandle(-11); [uint32]$m = 0\r\n"+
                    "if (-not [Jobs.RecoveryConsole]::GetConsoleMode($h, [ref]$m)) { throw 'Run in the original console.' }\r\n"+
                    "try {\r\nif (-not [Jobs.RecoveryConsole]::SetConsoleMode($h, ($m -bor 4))) { throw 'Cannot enable terminal recovery.' }\r\n"+
                    "[Console]::Write([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+encoded+"')))\r\n"+
                    "[Console]::ForegroundColor = [ConsoleColor]"+((int)state.Foreground)+"\r\n"+
                    "[Console]::BackgroundColor = [ConsoleColor]"+((int)state.Background)+"\r\n"+
                    "[Console]::Write([string][char]27 + '[39;49m')\r\n"+
                    "} finally { [void][Jobs.RecoveryConsole]::SetConsoleMode($h, $m) }\r\n";
                File.WriteAllText(state.Recovery,manual,new UTF8Encoding(false));
                state.Owner = identity+":"+Process.GetCurrentProcess().Id+":"+Process.GetCurrentProcess().StartTime.ToUniversalTime().Ticks;
                Environment.SetEnvironmentVariable(OwnerName,state.Owner);
                state.Active = true;
                foreach (string key in Keys) { Console.Write(Escape(key,state.Applied[key])); }
                Console.ForegroundColor = ConsoleColor.White; Console.BackgroundColor = ConsoleColor.Black;
                Dictionary<string,string> check = Query(state);
                foreach (string key in Keys) {
                    if (check == null || Normal(check[key]) != Normal(state.Applied[key])) { Restore(state); Plain(state); return; }
                }
            } catch (Exception error) {
                Restore(state); Plain(state);
                Console.Error.WriteLine("[Jobs] Terminal style unavailable: " + error.Message);
            }
        }
        public static void Restore(State state) {
            if (state == null) { return; }
            try {
                if (state.Active) {
                    Dictionary<string,string> current = Query(state);
                    bool complete = current != null;
                    if (current != null) {
                        bool restoreForeground = Console.ForegroundColor == ConsoleColor.White && Normal(current["10"]) == Normal(state.Applied["10"]) && Normal(current["4;15"]) == Normal(state.Applied["4;15"]);
                        bool restoreBackground = Console.BackgroundColor == ConsoleColor.Black && Normal(current["11"]) == Normal(state.Applied["11"]) && Normal(current["4;0"]) == Normal(state.Applied["4;0"]);
                        foreach (string key in Keys) {
                            if (Normal(current[key]) == Normal(state.Applied[key])) { Console.Write(Escape(key,state.Original[key])); }
                            else if (Normal(current[key]) != Normal(state.Original[key])) {
                                complete = false; Console.Error.WriteLine("[Jobs] Kept a concurrent color change: " + key);
                            }
                        }
                        if (restoreForeground) { Console.ForegroundColor = state.Foreground; Console.Write("\x1b[39m"); }
                        if (restoreBackground) { Console.BackgroundColor = state.Background; Console.Write("\x1b[49m"); }
                    }
                    if (complete) {
                        Dictionary<string,string> check = Query(state);
                        foreach (string key in Keys) { if (check == null || Normal(check[key]) != Normal(state.Original[key])) { complete = false; } }
                    }
                    if (complete) { File.Delete(state.Recovery); }
                    else { Console.Error.WriteLine("[Jobs] Color restore needs review. Manual recovery: powershell -NoProfile -File \""+state.Recovery+"\""); }
                }
            } catch (Exception error) {
                Console.Error.WriteLine("[Jobs] Color restore failed: "+error.Message+"; recovery: "+state.Recovery);
            } finally {
                if (state.Owner != null && Environment.GetEnvironmentVariable(OwnerName) == state.Owner) { Environment.SetEnvironmentVariable(OwnerName,state.PreviousOwner); }
                state.Active = false;
                uint currentMode;
                if (state.ModeChanged && GetConsoleMode(state.Output,out currentMode) && currentMode == (state.OutputMode | 4)) { SetConsoleMode(state.Output,state.OutputMode); }
                state.ModeChanged = false;
                if (state.Fallback) {
                    foreach (KeyValuePair<string,string> pair in state.EnvironmentBefore) {
                        string applied = pair.Key == "FORCE_COLOR" || pair.Key == "CLICOLOR" ? "0" : "1";
                        if (Environment.GetEnvironmentVariable(pair.Key) == applied) { Environment.SetEnvironmentVariable(pair.Key,pair.Value); }
                    }
                    state.Fallback = false;
                }
            }
        }
    }
}
'@
        } catch {
            [Console]::Error.WriteLine('[Jobs] Terminal style setup failed; using plain output: ' + $_.Exception.Message)
            return @{ JobsTerminalPlainFallback = $true; Before = @{} }
        }
    }
    return New-Object Jobs.TerminalStyleV1.Native+State
}
# Guard setup is optional; failure keeps business behavior and the user's original terminal settings.
function Start-JobsTerminalStyle {
    param($State)
    if ($State -is [Collections.IDictionary] -and $State.Contains('JobsTerminalPlainFallback')) {
        foreach ($key in @('NO_COLOR', 'PLAIN_OUTPUT', 'FORCE_COLOR', 'CLICOLOR', 'ANSI_COLORS_DISABLED')) {
            $State.Before[$key] = [Environment]::GetEnvironmentVariable($key)
            [Environment]::SetEnvironmentVariable($key, $(if (@('FORCE_COLOR', 'CLICOLOR') -contains $key) { '0' } else { '1' }))
        }
        return
    }
    if ($null -ne $State) { [Jobs.TerminalStyleV1.Native]::Enter($State) }
}
# A finally block also runs for script exit and Ctrl+C; direct .NET calls avoid stopped pipelines.
function Stop-JobsTerminalStyle {
    param($State)
    if ($State -is [Collections.IDictionary] -and $State.Contains('JobsTerminalPlainFallback')) {
        foreach ($key in $State.Before.Keys) {
            $applied = if (@('FORCE_COLOR', 'CLICOLOR') -contains $key) { '0' } else { '1' }
            if ([Environment]::GetEnvironmentVariable($key) -ceq $applied) { [Environment]::SetEnvironmentVariable($key, $State.Before[$key]) }
        }
        return
    }
    if ($null -ne $State) { [Jobs.TerminalStyleV1.Native]::Restore($State) }
}
# END JOBS_TERMINAL_STYLE_V1

$__jobsTerminalStyleState = $null
$__jobsTerminalExitCode = 0
try {
    $__jobsTerminalStyleState = New-JobsTerminalStyleState
    Start-JobsTerminalStyle $__jobsTerminalStyleState
    if ($null -eq $__jobsTerminalCommand -or $__jobsTerminalCommand.Count -eq 0) { throw 'A program is required.' }
    $__jobsTerminalProgram = $__jobsTerminalCommand[0]
    $__jobsTerminalArguments = @()
    if ($__jobsTerminalCommand.Count -gt 1) { $__jobsTerminalArguments = @($__jobsTerminalCommand[1..($__jobsTerminalCommand.Count-1)]) }
    $LASTEXITCODE = 0
    & $__jobsTerminalProgram @__jobsTerminalArguments
    $__jobsTerminalCommandSucceeded = $?
    $__jobsTerminalExitCode = $LASTEXITCODE
    if (-not $__jobsTerminalCommandSucceeded -and $__jobsTerminalExitCode -eq 0) { $__jobsTerminalExitCode = 1 }
} finally {
    Stop-JobsTerminalStyle $__jobsTerminalStyleState
}
exit $__jobsTerminalExitCode
"""
    _interrupted = False
    # 等监督进程完成恢复后再退出，避免 Ctrl+C 提前关闭控制终端。
    def _wait(_arguments):
        nonlocal _interrupted
        _process = _subprocess.Popen(_arguments, env=_environment)
        while True:
            try:
                return _process.wait()
            except KeyboardInterrupt:
                _interrupted = True
                continue
    try:
        if _os.name == "nt":
            _powershell = _shutil.which("powershell.exe") or _shutil.which("pwsh.exe")
            if not _powershell:
                _os.environ.update(NO_COLOR="1", PLAIN_OUTPUT="1", FORCE_COLOR="0", CLICOLOR="0")
                return
            with _tempfile.TemporaryDirectory(prefix="jobs-terminal-style-") as _directory:
                _wrapper = _os.path.join(_directory, "guard.ps1")
                with open(_wrapper, "w", encoding="utf-8-sig", newline="\n") as _file:
                    _file.write(_powershell_core)
                # 原参数经 JSON 交给原生 Python 数组，避开旧 Windows PowerShell 的参数重解析。
                _environment["JOBS_TERMINAL_STYLE_PYTHON_COMMAND"] = _json.dumps(_command, ensure_ascii=False)
                _receipt = _os.path.join(_directory, "started")
                _environment["JOBS_TERMINAL_STYLE_PYTHON_RECEIPT"] = _receipt
                _bridge_source = """import json, os, subprocess, sys
command = json.loads(os.environ.pop('JOBS_TERMINAL_STYLE_PYTHON_COMMAND'))
with open(os.environ.pop('JOBS_TERMINAL_STYLE_PYTHON_RECEIPT'), 'wb') as receipt:
    receipt.write(b'started')
process = subprocess.Popen(command)
while True:
    try:
        result = process.wait()
        break
    except KeyboardInterrupt:
        continue
sys.exit(result if result >= 0 else 128 - result)
"""
                _bridge = "exec(__import__('base64').b64decode('" + _base64.b64encode(_bridge_source.encode()).decode() + "'))"
                _result = _wait([_powershell, "-NoProfile", "-ExecutionPolicy", "Bypass",
                                 "-File", _wrapper, _sys.executable, "-c", _bridge])
                if not _os.path.exists(_receipt) and not _interrupted and _result not in (129, 130, 143, -1073741510, 0xC000013A):
                    _os.environ.update(NO_COLOR="1", PLAIN_OUTPUT="1", FORCE_COLOR="0", CLICOLOR="0")
                    print("终端配色保护未能启动，保持原配色并使用纯文本。", file=_sys.stderr)
                    return
        else:
            _result = _wait(["/bin/sh", "-c", _shell_core + '\njobs_terminal_style_run "$@"\n',
                             "jobs-terminal-style", *_command])
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except OSError:
        _os.environ.update(NO_COLOR="1", PLAIN_OUTPUT="1", FORCE_COLOR="0", CLICOLOR="0")
        print("终端配色保护未能启动，保持原配色并使用纯文本。", file=_sys.stderr)
        return
    if _result in (-1073741510, 0xC000013A):
        raise SystemExit(130)
    raise SystemExit(_result if _result >= 0 else 128 - _result)


if __name__ == "__main__":
    _jobs_terminal_style_bootstrap_v1()
# JOBS_TERMINAL_STYLE_GUARD_V1_END

import html
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys

from PySide6.QtCore import Qt, QSettings, QStandardPaths, QTimer
from PySide6.QtGui import QColor, QFont, QKeySequence, QPalette, QShortcut, QAction, QActionGroup
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QLineEdit, QScrollArea, QFrame, QStackedWidget,
    QComboBox, QSlider, QMessageBox, QMenu, QSizePolicy, QDialog, QTextBrowser, QLayout,
)
from .catalog import Catalog
from .speech import Speech

STYLE = """
QWidget { color: #283b36; font-size: 14px; }
QMainWindow, QDialog, QWidget#content { background: #f6f7f3; }
QWidget#sidebar { background: #e8eee6; border-right: 1px solid #d6dfd4; }
QLabel#brand { font-size: 24px; font-weight: 700; }
QLabel#eyebrow { color: #718177; font-size: 11px; letter-spacing: 2px; }
QLabel#heading { font-size: 29px; font-weight: 700; }
QLabel#muted { color: #6c7a73; }
QLabel#notice { color: #64734d; background: #edf1df; padding: 12px; border-radius: 8px; }
QPushButton { background: #ffffff; border: 1px solid #dbe2d8; border-radius: 7px; padding: 8px 12px; }
QPushButton:hover { background: #edf2e8; border-color: #8caa8a; }
QPushButton:focus { border: 2px solid #698263; }
QPushButton:checked { background: #355744; color: white; border-color: #355744; }
QPushButton:disabled { color: #abb4a7; background: #f1f3ed; }
QPushButton#level { text-align: left; padding: 10px 14px; background: transparent; border: none; }
QPushButton#level:checked { background: #355744; color: white; }
QPushButton#word { text-align: left; border: none; background: transparent; padding: 0; font-size: 23px; font-weight: 650; color: #305d44; }
QPushButton#titleWord { text-align: left; border: none; background: transparent; padding: 0; font-size: 38px; font-weight: 700; color: #305d44; }
QPushButton#word:hover, QPushButton#titleWord:hover { color: #639144; }
QLineEdit, QComboBox { background: white; border: 1px solid #d5ded3; border-radius: 7px; padding: 9px; }
QFrame#card { background: white; border: 1px solid #dde4da; border-radius: 10px; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QStatusBar { background: #e8eee6; color: #586c5e; }
QTextBrowser, QComboBox QAbstractItemView, QMenu { background: white; color: #283b36; }
QMenu::item:selected { background: #355744; color: white; }
QToolTip { background: #fff; color: #283b36; border: 1px solid #d5ded3; }
"""


DARK_COLORS = {
    "#283b36": "#e1ebe5", "#f6f7f3": "#1c2521", "#e8eee6": "#25332b",
    "#d6dfd4": "#46574a", "#718177": "#a8baac", "#6c7a73": "#afc0b5",
    "#64734d": "#d0dbaa", "#edf1df": "#35412b", "#ffffff": "#29372f",
    "#dbe2d8": "#4a5d4f", "#edf2e8": "#374b3d", "#8caa8a": "#a0bf99",
    "#698263": "#9fbc94", "#355744": "#3b674e", "#abb4a7": "#809285",
    "#f1f3ed": "#263129", "#305d44": "#9bd5ac", "#639144": "#c2e9a2",
    "#d5ded3": "#4a5d4f", "#dde4da": "#46574a", "#586c5e": "#b0c5b5",
    "#fff": "#29372f", "#344a3b": "#d2e4d6", "#88977c": "#a9bd98",
}


def themed_text(text, dark):
    return re.sub(r"#[0-9a-fA-F]{6}|#fff\b",
                  lambda match: DARK_COLORS.get(match.group(), match.group()) if dark else match.group(), text)


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(wrap)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, name=None):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if name:
        widget.setObjectName(name)
    widget.clicked.connect(callback)
    return widget


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            clear_layout(item.layout())


def scroll_container():
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    body = QWidget()
    layout = QVBoxLayout(body)
    layout.setContentsMargins(0, 0, 12, 0)
    layout.setSpacing(12)
    layout.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
    scroll.setWidget(body)
    return scroll, layout


class Window(QMainWindow):
    PAGE_SIZE = 35

    def __init__(self, catalog=None, speech=None):
        super().__init__()
        self.catalog = catalog or Catalog()
        self.settings = QSettings("Jobs", "JobsEnglishWordBook")
        self.speech = speech or Speech(self)
        self.speech.message.connect(self.statusBar().showMessage)
        self.levels = self.catalog.levels()
        self.level_id = self.levels[0]["id"]
        self.letter = ""
        self.page = 0
        self.detail_word = None
        self.setWindowTitle("Jobs EnglishWordBook · 分级英语词典")
        self.resize(1220, 850)
        self.setMinimumSize(920, 640)
        self.theme_mode = self.settings.value("appearance/theme", "system")
        self.theme_dark = False
        self._changing_theme = False
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(self.make_sidebar())
        self.stack = QStackedWidget()
        self.stack.setObjectName("content")
        root_layout.addWidget(self.stack, 1)
        self.stack.addWidget(self.make_list())
        self.stack.addWidget(self.make_detail())
        self.setCentralWidget(root)
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.system_theme_changed)
        self.set_theme(self.theme_mode)
        QShortcut(QKeySequence("Escape"), self, activated=self.go_back)
        QShortcut(QKeySequence.StandardKey.Find, self, activated=self.focus_search)
        chosen = self.settings.value("level", self.level_id)
        self.choose_level(chosen if chosen in self.level_buttons else self.level_id)
        self.statusBar().showMessage("点击单词朗读 · 点击释义查看例句 · 词库可离线使用")

    def make_sidebar(self):
        side = QWidget()
        side.setObjectName("sidebar")
        layout = QVBoxLayout(side)
        layout.setContentsMargins(18, 28, 18, 18)
        layout.setSpacing(7)
        layout.addWidget(label("JOBS / LANGUAGE", "eyebrow"))
        self.brand = label("EnglishWordBook", "brand")
        layout.addWidget(self.brand)
        # 根据实际字体度量预留标题空间，避免系统缩放后裁切。
        self.brand.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.brand.ensurePolished()
        side.setFixedWidth(max(232, self.brand.sizeHint().width() + 36))
        layout.addWidget(label("把单词放回句子里。", "muted"))
        self.theme_button = button("主题", self.show_theme_menu)
        self.theme_button.setAccessibleName("切换主题：白天、黑夜、跟随系统")
        self.theme_menu = QMenu(self.theme_button)
        self.theme_group = QActionGroup(self)
        self.theme_actions = {}
        for title, mode in [("白天", "light"), ("黑夜", "dark"), ("跟随系统", "system")]:
            action = QAction(title, self)
            action.setCheckable(True)
            action.triggered.connect(lambda checked, value=mode: self.set_theme(value))
            self.theme_group.addAction(action)
            self.theme_menu.addAction(action)
            self.theme_actions[mode] = action
        layout.addWidget(self.theme_button)
        layout.addSpacing(7)
        layout.addWidget(label("选择学习难度", "eyebrow"))
        level_scroll, level_layout = scroll_container()
        level_layout.setContentsMargins(0, 0, 0, 0)
        level_layout.setSpacing(3)
        self.level_buttons = {}
        for level in self.levels:
            b = button(level["name"], lambda: None, "level")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.toggled.connect(lambda checked, key=level["id"]: self.choose_level(key) if checked else None)
            level_layout.addWidget(b)
            self.level_buttons[level["id"]] = b
        level_layout.addStretch()
        layout.addWidget(level_scroll, 1)
        layout.addWidget(label("英语发音", "eyebrow"))
        self.voice_combo = QComboBox()
        for voice in self.speech.voices:
            self.voice_combo.addItem(f"{voice.name()} · {voice.locale().name()}")
        if self.speech.voices:
            current = self.speech.engine.voice()
            self.voice_combo.setCurrentIndex(next((i for i, v in enumerate(self.speech.voices) if v == current), 0))
        else:
            self.voice_combo.addItem("系统未安装英语语音")
            self.voice_combo.setEnabled(False)
        self.voice_combo.currentIndexChanged.connect(self.speech.set_voice)
        layout.addWidget(self.voice_combo)
        layout.addWidget(label("语速  慢 ← → 快", "muted"))
        rate = QSlider(Qt.Orientation.Horizontal)
        rate.setRange(-70, 50)
        rate.setValue(-15)
        rate.valueChanged.connect(self.speech.set_rate)
        layout.addWidget(rate)
        layout.addWidget(button("停止朗读", self.speech.stop))
        layout.addWidget(button("词库与分级说明", self.show_sources))
        return side

    def show_theme_menu(self):
        self.theme_menu.popup(self.theme_button.mapToGlobal(self.theme_button.rect().bottomLeft()))

    def set_theme(self, mode):
        self.theme_mode = mode if mode in self.theme_actions else "system"
        self.settings.setValue("appearance/theme", self.theme_mode)
        hints = QApplication.instance().styleHints()
        self._changing_theme = True
        try:
            if self.theme_mode == "system":
                hints.unsetColorScheme()
            else:
                hints.setColorScheme(Qt.ColorScheme.Dark if self.theme_mode == "dark" else Qt.ColorScheme.Light)
        finally:
            self._changing_theme = False
        self.theme_actions[self.theme_mode].setChecked(True)
        self.theme_button.setText("主题 · " + self.theme_actions[self.theme_mode].text())
        self.system_theme_changed(hints.colorScheme())

    def system_theme_changed(self, scheme):
        if self._changing_theme:
            return
        self.theme_dark = self.theme_mode == "dark" or (self.theme_mode == "system" and scheme == Qt.ColorScheme.Dark)
        palette = QPalette()
        for role, color in {
            QPalette.ColorRole.Window: "#f6f7f3", QPalette.ColorRole.WindowText: "#283b36",
            QPalette.ColorRole.Base: "#ffffff", QPalette.ColorRole.Text: "#283b36",
            QPalette.ColorRole.Button: "#ffffff", QPalette.ColorRole.ButtonText: "#283b36",
            QPalette.ColorRole.Highlight: "#355744", QPalette.ColorRole.HighlightedText: "#ffffff",
            QPalette.ColorRole.PlaceholderText: "#6c7a73", QPalette.ColorRole.Link: "#305d44",
            QPalette.ColorRole.ToolTipBase: "#ffffff", QPalette.ColorRole.ToolTipText: "#283b36",
        }.items():
            palette.setColor(role, QColor(themed_text(color, self.theme_dark) if role != QPalette.ColorRole.HighlightedText else color))
        self.setPalette(palette)
        self.setStyleSheet(themed_text(STYLE.replace("background: white", "background: #ffffff"), self.theme_dark))
        for widget in self.findChildren(QLabel):
            source = widget.property("themeHtml")
            if source:
                widget.setText(themed_text(source, self.theme_dark))

    def set_link_text(self, widget, text):
        widget.setProperty("themeHtml", text)
        widget.setText(themed_text(text, self.theme_dark))

    def make_list(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 26, 18)
        layout.setSpacing(14)
        layout.addWidget(label("YOUR WORDS, IN CONTEXT", "eyebrow"))
        self.heading = label("", "heading")
        layout.addWidget(self.heading)
        self.summary = label("", "muted")
        layout.addWidget(self.summary)
        self.notice = label("", "notice", True)
        layout.addWidget(self.notice)
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索当前难度中的单词或中文释义…")
        self.search.setClearButtonEnabled(True)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self.search_changed)
        self.search.textChanged.connect(lambda: self.search_timer.start())
        layout.addWidget(self.search)
        letters = QHBoxLayout()
        letters.setSpacing(3)
        self.letter_buttons = {}
        for letter in ["", *"ABCDEFGHIJKLMNOPQRSTUVWXYZ", "#"]:
            b = button(letter or "全部", lambda: None)
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.toggled.connect(lambda checked, value=letter: self.choose_letter(value) if checked else None)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            b.setMinimumWidth(0)
            b.setStyleSheet("padding: 7px 0; font-size: 12px;")
            self.letter_buttons[letter] = b
            letters.addWidget(b)
        layout.addLayout(letters)
        layout.addWidget(label("单词 / 点击发音                         全部已收录释义 / 点击查看用法", "muted"))
        self.list_scroll, self.cards = scroll_container()
        layout.addWidget(self.list_scroll, 1)
        footer = QHBoxLayout()
        self.page_label = label("", "muted")
        footer.addWidget(self.page_label, 1)
        self.previous = button("上一页", lambda: self.change_page(-1))
        self.next = button("下一页", lambda: self.change_page(1))
        footer.addWidget(self.previous)
        footer.addWidget(self.next)
        layout.addLayout(footer)
        return page

    def make_detail(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 25, 26, 18)
        back = button("← 返回单词列表  /  Esc", self.go_back)
        layout.addWidget(back, alignment=Qt.AlignmentFlag.AlignLeft)
        self.detail_scroll, self.detail_layout = scroll_container()
        layout.addWidget(self.detail_scroll, 1)
        return page

    def choose_level(self, key):
        self.speech.stop()
        self.level_id, self.letter, self.page = key, "", 0
        self.settings.setValue("level", key)
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.search_timer.stop()
        self.stack.setCurrentIndex(0)
        for k, b in self.level_buttons.items():
            b.blockSignals(True)
            b.setChecked(k == key)
            b.blockSignals(False)
        level = next(l for l in self.levels if l["id"] == key)
        self.heading.setText(level["name"])
        self.notice.setText(level["description"])
        self.refresh()

    def choose_letter(self, value):
        self.letter, self.page = value, 0
        self.refresh()

    def search_changed(self):
        self.letter, self.page = "", 0
        self.refresh()

    def change_page(self, delta):
        self.page += delta
        self.refresh()

    def refresh(self):
        counts = self.catalog.initials(self.level_id, self.search.text())
        for key, b in self.letter_buttons.items():
            b.blockSignals(True)
            b.setChecked(key == self.letter)
            b.blockSignals(False)
            b.setEnabled(not key or counts.get(key, 0) > 0 or key == self.letter)
            b.setToolTip(f"{key or '全部'}：{counts.get(key, 0) if key else sum(counts.values()):,} 个词条")
        total = self.catalog.count(self.level_id, self.letter, self.search.text())
        all_count = self.catalog.count(self.level_id)
        self.page = min(max(0, self.page), max(0, (total - 1) // self.PAGE_SIZE))
        self.summary.setText(f"{all_count:,} 个收录词条  ·  A–Z 字母分区  ·  本地词库")
        clear_layout(self.cards)
        self.visible_words = self.catalog.words(self.level_id, self.letter, self.search.text(), self.page * self.PAGE_SIZE, self.PAGE_SIZE)
        for word in self.visible_words:
            self.cards.addWidget(self.word_card(word))
        if not total:
            self.cards.addWidget(label("没有匹配的词条。请尝试其他拼写或清空搜索。", "muted", True))
        self.cards.addStretch()
        pages = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page_label.setText(f"{self.letter or '全部字母'}  ·  {total:,} 个结果  ·  第 {self.page + 1} / {pages} 页")
        self.previous.setEnabled(self.page > 0)
        self.next.setEnabled((self.page + 1) * self.PAGE_SIZE < total)
        self.list_scroll.verticalScrollBar().setValue(0)

    def word_card(self, word):
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        row = QHBoxLayout(card)
        row.setContentsMargins(20, 18, 20, 18)
        row.setSpacing(25)
        left = QVBoxLayout()
        left.setSpacing(6)
        speak = button(word["word"], lambda: self.speech.say(word["word"]), "word")
        speak.setToolTip("点击朗读 " + word["word"])
        left.addWidget(speak, alignment=Qt.AlignmentFlag.AlignLeft)
        left.addWidget(label(word["phonetic"] or "英语点读", "muted", True))
        left.addStretch()
        left_widget = QWidget()
        left_widget.setFixedWidth(210)
        left_widget.setLayout(left)
        row.addWidget(left_widget, 0, Qt.AlignmentFlag.AlignTop)
        right = QVBoxLayout()
        right.setSpacing(8)
        for i, sense in enumerate(word["senses"]):
            entry = QLabel()
            entry.setWordWrap(True)
            entry.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
            entry.setTextFormat(Qt.TextFormat.RichText)
            entry.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.LinksAccessibleByKeyboard)
            self.set_link_text(entry, f'<a style="color:#344a3b;text-decoration:none" href="{i}"><span style="color:#88977c">{i+1:02d} · {html.escape(sense["pos"])}</span>  {html.escape(sense["meaning"])}  →</a>')
            entry.linkActivated.connect(lambda target, wid=word["id"]: self.open_detail(wid, int(target)))
            entry.setAccessibleName(f'{sense["pos"]} {sense["meaning"]}，查看例句')
            right.addWidget(entry)
        right.addStretch()
        row.addLayout(right, 1)
        return card

    def open_detail(self, word_id, sense_index):
        word = self.catalog.word(word_id)
        self.detail_word = word
        sense = word["senses"][sense_index]
        clear_layout(self.detail_layout)
        self.detail_layout.addWidget(label("WORD / MEANING / CONTEXT", "eyebrow"))
        self.detail_layout.addWidget(button(word["word"], lambda: self.speech.say(word["word"]), "titleWord"))
        self.detail_layout.addWidget(label((word["phonetic"] or "") + "  ·  点击标题发音", "muted"))
        self.detail_layout.addWidget(label(f'{sense["pos"]}  {sense["meaning"]}', "heading", True))
        if sense.get("english"):
            self.detail_layout.addWidget(label(sense["english"], "muted", True))
        self.detail_layout.addWidget(label("例句与短语 · 点击英文朗读", "brand"))
        self.detail_layout.addWidget(label("以下为该词的参考用法。原始词库未提供逐义对应关系，例句不一定对应当前所选释义。", "notice", True))
        self.example_buttons = []
        for index, example in enumerate(word["examples"]):
            self.detail_layout.addWidget(self.example_card(example, index + 1))
        if not word["examples"]:
            self.detail_layout.addWidget(label("当前词库尚未收录该词例句。可先学习下方短语；缺失内容不以自动拼接句子代替。", "muted", True))
        if word["phrases"]:
            self.detail_layout.addWidget(label("常用短语", "brand"))
            for index, phrase in enumerate(word["phrases"]):
                self.detail_layout.addWidget(self.example_card(phrase, index + 1))
        self.detail_layout.addWidget(label("词条来源：" + "、".join(word["sources"]), "muted", True))
        self.detail_layout.addStretch()
        self.detail_scroll.verticalScrollBar().setValue(0)
        self.stack.setCurrentIndex(1)

    def example_card(self, example, number):
        card = QFrame()
        card.setObjectName("card")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        sentence = QLabel()
        sentence.setWordWrap(True)
        sentence.setTextFormat(Qt.TextFormat.RichText)
        self.set_link_text(sentence, f'<a href="speak" style="color:#305d44;text-decoration:none;font-size:18px">{number:02d} &nbsp; {html.escape(example["en"])}</a>')
        sentence.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse | Qt.TextInteractionFlag.LinksAccessibleByKeyboard)
        sentence.linkActivated.connect(lambda _: self.speech.say(example["en"]))
        sentence.setAccessibleName(example["en"] + "，点击朗读")
        self.example_buttons.append(sentence)
        layout.addWidget(sentence)
        if example.get("zh"):
            layout.addWidget(label(example["zh"], "muted", True))
        return card

    def go_back(self):
        self.stack.setCurrentIndex(0)

    def focus_search(self):
        self.go_back()
        self.search.setFocus()
        self.search.selectAll()

    def show_sources(self):
        report = self.catalog.report()
        dialog = QDialog(self)
        dialog.setWindowTitle("词库来源与覆盖范围")
        dialog.resize(720, 580)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        rows = "".join(f'<tr><td>{html.escape(x["name"])}</td><td>{x["count"]:,}</td></tr>' for x in report["levels"])
        browser.setHtml(f'''<h2>真实收录，透明分级</h2><p>全库 {report["words"]:,} 个词条，{report["examples"]:,} 条去重例句。缺例句词条 {report["words_without_examples"]:,} 个。</p>
        <p>初中、高中、CET4、CET6、专八采用公开备考词书合集，较高学段包含较低学段基础词。完整覆盖本软件所列来源，不代表官方最新大纲的全部词汇或词典的所有义项。</p>
        <p>雅思 1～7 分为本软件学习目标档位：基础词与雅思词合并后按词频排序，累计收录。它不是官方分数词表，也不代表掌握这些词即可取得对应分数。</p>
        <table cellpadding="7"><tr><th>级别</th><th>词条数</th></tr>{rows}</table>
        <p>所有原始中文释义保留并按词性、分号分义；例句与短语保留原文，不伪造逐义映射。</p>
        <p><a href="https://github.com/kajweb/dict">备考词书来源：kajweb/dict</a> · <a href="https://github.com/rspeer/wordfreq">词频排序：wordfreq 3.1.1</a> · <a href="https://ielts.org/take-a-test/your-results/ielts-scoring-in-detail">IELTS 官方评分说明</a></p>
        <p>备考词书来源未提供清晰的再分发许可；当前作为个人学习资料。公开发行前应替换为已授权数据。系统语音由本机提供。</p>''')
        layout.addWidget(browser)
        layout.addWidget(button("关闭", dialog.accept))
        dialog.exec()

    def closeEvent(self, event):
        self.speech.stop()
        self.catalog.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JobsEnglishWordBook")
    app.setOrganizationName("Jobs")
    app.setStyle("Fusion")
    font = QFont("PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei", 11)
    app.setFont(font)
    log_dir = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(log_dir / "app.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")])
    def handle_error(kind, value, tb):
        logging.error("未处理异常", exc_info=(kind, value, tb))
        QMessageBox.critical(None, "运行异常", f"{value}\n日志：{log_dir}")
    sys.excepthook = handle_error
    try:
        window = Window()
    except Exception as exc:
        logging.exception("启动失败")
        QMessageBox.critical(None, "启动失败", str(exc))
        return 1
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
