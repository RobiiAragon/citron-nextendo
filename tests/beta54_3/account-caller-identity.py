#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compile actual account methods against synthetic process/account boundaries."""
import argparse
from pathlib import Path
import subprocess
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--compiler", required=True)
parser.add_argument("--sanitizers", action="store_true")
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
text = (repo / "src/core/hle/service/acc/acc.cpp").read_text()


def method(signature):
    start = text.index(signature)
    brace = text.index("{", start)
    end = brace + 1
    depth = 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


source = r'''
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <string>
#include <unordered_set>
using u64 = std::uint64_t;
constexpr int ResultSuccess = 0;
constexpr u64 island = 0x01006F8002326000ULL;
constexpr u64 other = 0x0100152000022000ULL;
u64 linked = 123456, response = 0, version_title = 0;
bool version_ok = true, baas_mode = false;
#define LOG_DEBUG(...)
#define LOG_WARNING(...)
struct Process { u64 id; u64 GetProgramId() const { return id; } };
struct Thread { Process* process; Process* GetOwnerProcess() { return process; } };
struct HLERequestContext { Thread thread; Thread& GetThread() { return thread; } };
namespace Core { struct System { u64 GetApplicationProcessProgramID() { return island; } }; }
namespace Common {
namespace UchAccountTransport { bool Enabled(u64) { return false; } }
namespace NextendoAccount {
u64 GetPid() { return linked; }
bool IsLinked() { return linked != 0; }
}
}
namespace Nextendo::CompatibleTitles {
const std::unordered_set<u64>& Table() { static const std::unordered_set<u64> table{island, other}; return table; }
bool IsVersionOk(u64, const std::string&) { return version_ok; }
}
u64 ConfiguredTestPid() { return 0; }
std::string GetInstalledTitleVersion(Core::System&, u64 id) { version_title = id; return "synthetic"; }
bool TitleUsesBaasNsa(u64 id) { return id == island; }
void SetBaasNsaMode(bool mode) { baas_mode = mode; }
u64 GetLinkedAccountBaasNsa() { return 654321; }
u64 ChooseAnnouncedNsa(u64 id, u64 account, u64 nsa) { return id == island ? nsa : account; }
namespace IPC {
struct ResponseBuilder {
    ResponseBuilder(HLERequestContext&, int) {}
    void Push(int) {}
    template<class T> void PushRaw(T id) { response = id; }
};
}
'''
source += method("u64 GetCallerProgramId(")
source += "\nstruct Manager { Core::System actual_system; Core::System& system = actual_system;\n"
for signature in ("    u64 GetEffectivePid(", "    static bool IsLinkedAccountPid(",
                  "    u64 AnnouncedAccountId(", "    void GetAccountId("):
    source += method(signature) + "\n"
source += r'''};
int main() {
    Manager manager;
    Process process{other};
    HLERequestContext context{{&process}};
    // The global application is ACNH, but this IPC came from another process.
    manager.GetAccountId(context);
    assert(response == linked && version_title == other && !baas_mode);
    process.id = island;
    manager.GetAccountId(context);
    assert(response == 654321 && version_title == island && baas_mode);
    version_ok = false;
    manager.GetAccountId(context);
    assert(response == 0xcafe && !baas_mode);
    version_ok = true;
    linked = 0;
    manager.GetAccountId(context);
    assert(response == 0xcafe && !baas_mode);
    context.thread.process = nullptr;
    assert(GetCallerProgramId(context) == 0);
}
'''
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    cpp = root / "account.cpp"
    cpp.write_text(source)
    command = [args.compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror", str(cpp), "-o", str(root / "account")]
    if args.sanitizers:
        command += ["-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
    subprocess.run(command, check=True)
    subprocess.run([str(root / "account")], check=True, timeout=10)
