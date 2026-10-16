from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os, subprocess, sys

@dataclass(frozen=True)
class ModelItem:
    kind: str
    reference: str

def application_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1]

class Backend:
    def __init__(self, executable: Path | None = None):
        self.executable = executable or application_directory() / "iec61850-bridge.exe"
        self.tls = None

    def set_tls(self, enabled: bool, ca: str = "", cert: str = "", key: str = ""):
        self.tls = (ca, cert, key) if enabled else None

    def environment(self):
        env = os.environ.copy()
        if self.tls:
            env.update({"IEC61850_TLS_CA": self.tls[0], "IEC61850_TLS_CERT": self.tls[1], "IEC61850_TLS_KEY": self.tls[2]})
        return env

    def run(self, action: str, host: str, port: int, *args: str) -> str:
        if not self.executable.exists():
            raise RuntimeError(f"Native IEC61850-Komponente fehlt: {self.executable}")
        completed = subprocess.run([str(self.executable), action, host, str(port), *map(str, args)], capture_output=True, text=True, timeout=60, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=self.environment())
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or f"IEC61850-Aktion fehlgeschlagen ({completed.returncode})")
        return completed.stdout

    def probe(self, host: str, port: int) -> None: self.run("probe", host, port)
    def browse(self, host: str, port: int) -> list[ModelItem]:
        items=[]
        for line in self.run("browse", host, port).splitlines():
            if "\t" in line:
                kind, ref=line.split("\t",1); items.append(ModelItem(kind,ref))
        return items
    def read(self, host, port, reference, fc):
        output=self.run("read",host,port,reference,fc)
        return output.split("\t",1)[1] if output.startswith("VALUE\t") else output.strip()
    def write(self, host, port, reference, fc, value_type, value): self.run("write",host,port,reference,fc,value_type,value)
    def control(self, host, port, reference, value_type, value, action, origin, test, interlock, synchro):
        self.run("control",host,port,reference,value_type,value,action,origin,int(test),int(interlock),int(synchro))

    def start_report(self, host, port, rcb, dataset):
        return subprocess.Popen([str(self.executable), "report", host, str(port), rcb, dataset], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0), env=self.environment())

    def start_goose(self, interface):
        return subprocess.Popen([str(self.executable), "goose", interface], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0), env=self.environment())
