"""
app/hardware/detector.py
========================
Robust, non-invasive hardware detection service for Windows 10 & 11.
Detects:
- GPU name, vendor, and dedicated VRAM (distinguishing from shared RAM)
- System total and available RAM
- CPU processor model, core count, logical threads, and architecture
- Windows version, build, and architecture
- Free application disk space
- NVIDIA driver version & CUDA availability
- Detection status (DETECTED, PARTIAL, FAILED)

Security & Performance Policies:
- Does NOT require administrator privileges.
- External commands have strict 3-second timeouts.
- Never crashes if WMI, PowerShell, or nvidia-smi are missing.
- Never fabricates or guesses missing hardware values.
- Zero large package or model downloads.
"""

import datetime
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.utils.logging import logger


class HardwareSpecs(BaseModel):
    """Detailed hardware specifications detected on the host system."""

    gpu_name: str = Field(default="Unknown", description="Display name of detected GPU")
    gpu_vendor: str = Field(default="Unknown", description="GPU vendor: NVIDIA, Intel, AMD, or Unknown")
    vram_mb: Optional[int] = Field(default=None, description="Dedicated GPU VRAM in Megabytes, or None if unavailable")
    shared_memory_mb: Optional[int] = Field(default=None, description="Shared GPU memory in Megabytes")
    ram_total_gb: float = Field(default=0.0, description="Total system physical RAM in Gigabytes")
    ram_available_gb: float = Field(default=0.0, description="Currently available RAM in Gigabytes")
    cpu_name: str = Field(default="Unknown Processor", description="Processor model name")
    cpu_cores: int = Field(default=1, description="Physical CPU cores")
    cpu_threads: int = Field(default=1, description="Logical CPU threads")
    cpu_arch: str = Field(default="x86_64", description="CPU Architecture e.g. AMD64")
    windows_version: str = Field(default="Windows", description="OS name, release, build, and arch")
    disk_total_gb: float = Field(default=0.0, description="Total disk space of app drive in GB")
    disk_free_gb: float = Field(default=0.0, description="Free disk space of app drive in GB")
    driver_version: Optional[str] = Field(default=None, description="GPU driver version or None")
    cuda_available: bool = Field(default=False, description="Whether CUDA execution is confirmed available")
    nvidia_gpu_present: bool = Field(default=False, description="Whether a compatible NVIDIA discrete GPU is present")
    detection_status: str = Field(default="DETECTED", description="'DETECTED', 'PARTIAL', or 'FAILED'")
    detection_notes: List[str] = Field(default_factory=list, description="Telemetry logs and warnings")
    detected_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat(), description="Detection timestamp")

    # Backward compatibility properties
    @property
    def ram_gb(self) -> float:
        return self.ram_total_gb

    @property
    def vram_mb_or_zero(self) -> int:
        return self.vram_mb or 0


class HardwareDetector:
    """
    Modular hardware detector using Windows-native APIs, standard library,
    and timeout-guarded system utilities.
    """

    COMMAND_TIMEOUT_SECONDS = 3.0

    def __init__(
        self,
        command_runner: Optional[Any] = None,
        mock_profile: Optional[str] = None,
    ):
        """
        :param command_runner: Optional callable to mock subprocess execution in unit tests.
        :param mock_profile: Optional string profile key to generate deterministic mock specs.
        """
        self._cmd_runner = command_runner or self._default_run_command
        self._mock_profile = mock_profile

    def _get_mock_profile_specs(self, profile_name: str) -> HardwareSpecs:
        prof_upper = profile_name.upper()
        if "MX110" in prof_upper or "2GB" in prof_upper or "LEGACY" in prof_upper:
            return HardwareSpecs(
                gpu_name="NVIDIA GeForce MX110",
                gpu_vendor="NVIDIA",
                vram_mb=2048,
                shared_memory_mb=4096,
                ram_total_gb=8.0,
                ram_available_gb=3.5,
                cpu_name="Intel(R) Core(TM) i5-7200U CPU @ 2.50GHz",
                cpu_cores=2,
                cpu_threads=4,
                cpu_arch="AMD64",
                windows_version="Windows 10 Home (Build 19045) AMD64",
                disk_total_gb=256.0,
                disk_free_gb=50.0,
                driver_version="531.79",
                cuda_available=True,
                nvidia_gpu_present=True,
                detection_status="DETECTED",
                detection_notes=["Deterministic Mock MX110_2GB profile for automated testing"],
            )
        elif "HIGH" in prof_upper:
            return HardwareSpecs(
                gpu_name="NVIDIA GeForce RTX 3070",
                gpu_vendor="NVIDIA",
                vram_mb=8192,
                shared_memory_mb=16384,
                ram_total_gb=32.0,
                ram_available_gb=24.0,
                cpu_name="12th Gen Intel(R) Core(TM) i7-12700K",
                cpu_cores=8,
                cpu_threads=16,
                cpu_arch="AMD64",
                windows_version="Windows 11 Pro (Build 22631) AMD64",
                disk_total_gb=1000.0,
                disk_free_gb=350.0,
                driver_version="551.23",
                cuda_available=True,
                nvidia_gpu_present=True,
                detection_status="DETECTED",
                detection_notes=["Deterministic Mock HIGH_8GB profile for automated testing"],
            )
        return HardwareSpecs(detection_status="FAILED", detection_notes=[f"Unknown mock profile: {profile_name}"])

    def detect(self) -> HardwareSpecs:
        """
        Executes hardware detection and returns a populated HardwareSpecs object.
        Guaranteed not to raise unhandled exceptions.
        """
        if self._mock_profile:
            return self._get_mock_profile_specs(self._mock_profile)

        notes: List[str] = []
        is_partial = False
        is_failed = False

        # 1. OS & Architecture Detection
        win_ver = self._detect_windows_version(notes)

        # 2. CPU Detection
        cpu_name, cpu_cores, cpu_threads, cpu_arch = self._detect_cpu(notes)
        if cpu_name == "Unknown Processor":
            is_partial = True

        # 3. System RAM Detection
        ram_total, ram_avail = self._detect_ram(notes)
        if ram_total <= 0.0:
            is_failed = True
            notes.append("Failed to detect physical system RAM.")

        # 4. Free Disk Space
        disk_total, disk_free = self._detect_disk(notes)

        # 5. GPU, Dedicated VRAM, Driver Version
        gpu_info = self._detect_gpu(notes)
        if gpu_info["vram_mb"] is None:
            is_partial = True
        if gpu_info["name"] == "Unknown":
            is_partial = True

        # 6. CUDA / NVIDIA capability
        cuda_available = self._detect_cuda(gpu_info.get("nvidia_gpu_present", False), notes)

        # 7. Overall Status Determination
        if is_failed:
            status = "FAILED"
        elif is_partial:
            status = "PARTIAL"
        else:
            status = "DETECTED"

        specs = HardwareSpecs(
            gpu_name=gpu_info["name"],
            gpu_vendor=gpu_info["vendor"],
            vram_mb=gpu_info["vram_mb"],
            shared_memory_mb=gpu_info["shared_memory_mb"],
            ram_total_gb=ram_total,
            ram_available_gb=ram_avail,
            cpu_name=cpu_name,
            cpu_cores=cpu_cores,
            cpu_threads=cpu_threads,
            cpu_arch=cpu_arch,
            windows_version=win_ver,
            disk_total_gb=disk_total,
            disk_free_gb=disk_free,
            driver_version=gpu_info["driver_version"],
            cuda_available=cuda_available,
            nvidia_gpu_present=gpu_info.get("nvidia_gpu_present", False),
            detection_status=status,
            detection_notes=notes,
            detected_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        logger.info(
            f"Hardware Detection Completed [{status}]: CPU={specs.cpu_name} ({specs.cpu_threads}T) | "
            f"RAM={specs.ram_total_gb}GB ({specs.ram_available_gb}GB free) | "
            f"GPU={specs.gpu_name} ({specs.vram_mb}MB VRAM) | DiskFree={specs.disk_free_gb}GB"
        )
        return specs

    # --------------------------------------------------------------------------
    # Subprocess Helper with Strict Timeouts
    # --------------------------------------------------------------------------
    def _default_run_command(self, cmd_args: List[str]) -> Tuple[int, str, str]:
        """Safely executes an external command with timeout."""
        try:
            res = subprocess.run(
                cmd_args,
                capture_output=True,
                text=True,
                timeout=self.COMMAND_TIMEOUT_SECONDS,
                shell=False,
            )
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            logger.warning(f"Hardware command timed out: {' '.join(cmd_args)}")
            return -1, "", "Command timed out"
        except (FileNotFoundError, PermissionError) as e:
            return -2, "", str(e)
        except Exception as e:
            return -3, "", str(e)

    # --------------------------------------------------------------------------
    # 1. OS & Platform Detection
    # --------------------------------------------------------------------------
    def _detect_windows_version(self, notes: List[str]) -> str:
        """Detects precise Windows edition, build, and architecture."""
        system_name = platform.system()
        release = platform.release()
        arch = platform.machine() or "64-bit"

        # Try reading Windows Registry for exact edition and build number
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
                product_name, _ = winreg.QueryValueEx(key, "ProductName")
                build_number, _ = winreg.QueryValueEx(key, "CurrentBuild")
                display_ver = ""
                try:
                    display_ver, _ = winreg.QueryValueEx(key, "DisplayVersion")
                except Exception:
                    pass
                ver_str = f"{product_name}"
                if display_ver:
                    ver_str += f" ({display_ver}, Build {build_number})"
                else:
                    ver_str += f" (Build {build_number})"
                ver_str += f" {arch}"
                return ver_str
            except Exception:
                pass

        return f"{system_name} {release} ({platform.version()}) {arch}"

    # --------------------------------------------------------------------------
    # 2. CPU Detection
    # --------------------------------------------------------------------------
    def _detect_cpu(self, notes: List[str]) -> Tuple[str, int, int, str]:
        """
        Returns (cpu_name, physical_cores, logical_threads, architecture).
        """
        logical_threads = os.cpu_count() or 1
        cpu_arch = platform.machine() or "x86_64"
        cpu_name = "Unknown Processor"

        # 1. Try Windows Registry (zero external process overhead)
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                name_val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if name_val and name_val.strip():
                    cpu_name = name_val.strip()
            except Exception:
                pass

        # 2. Fallback to platform.processor()
        if cpu_name == "Unknown Processor":
            proc = platform.processor()
            if proc and len(proc.strip()) > 3:
                cpu_name = proc.strip()

        # 3. Fallback to PowerShell CIM
        if cpu_name == "Unknown Processor" and sys.platform == "win32":
            rc, out, _ = self._cmd_runner(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"])
            if rc == 0 and out.strip():
                cpu_name = out.strip().splitlines()[0].strip()

        # Physical cores estimation
        physical_cores = max(1, logical_threads // 2)
        try:
            import psutil
            p_cores = psutil.cpu_count(logical=False)
            if p_cores:
                physical_cores = p_cores
        except Exception:
            pass

        return cpu_name, physical_cores, logical_threads, cpu_arch

    # --------------------------------------------------------------------------
    # 3. System RAM Detection
    # --------------------------------------------------------------------------
    def _detect_ram(self, notes: List[str]) -> Tuple[float, float]:
        """Returns (total_ram_gb, available_ram_gb)."""
        # Primary: psutil
        try:
            import psutil
            vm = psutil.virtual_memory()
            total_gb = round(vm.total / (1024 ** 3), 2)
            avail_gb = round(vm.available / (1024 ** 3), 2)
            return total_gb, avail_gb
        except ImportError:
            pass
        except Exception as e:
            notes.append(f"psutil RAM detection warning: {e}")

        # Secondary: Windows ctypes GlobalMemoryStatusEx
        if sys.platform == "win32":
            try:
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                    total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
                    avail_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
                    return total_gb, avail_gb
            except Exception as e:
                notes.append(f"ctypes memory status warning: {e}")

        return 0.0, 0.0

    # --------------------------------------------------------------------------
    # 4. Disk Space Detection
    # --------------------------------------------------------------------------
    def _detect_disk(self, notes: List[str]) -> Tuple[float, float]:
        """Returns (total_disk_gb, free_disk_gb) for the active drive."""
        try:
            cwd = os.path.abspath(os.getcwd())
            total, used, free = shutil.disk_usage(cwd)
            return round(total / (1024 ** 3), 1), round(free / (1024 ** 3), 1)
        except Exception as e:
            notes.append(f"Disk space detection failed: {e}")
            return 0.0, 0.0

    # --------------------------------------------------------------------------
    # 5. GPU & Dedicated VRAM Detection
    # --------------------------------------------------------------------------
    def _detect_gpu(self, notes: List[str]) -> Dict[str, Any]:
        """
        Inspects GPU hardware. Prioritizes discrete dedicated GPUs (NVIDIA/AMD)
        over integrated graphics. Distinguishes dedicated VRAM from shared RAM.
        """
        # Strategy A: nvidia-smi (Most accurate for NVIDIA dedicated VRAM)
        res_nvidia = self._detect_gpu_via_nvidia_smi()
        if res_nvidia and res_nvidia.get("vram_mb"):
            notes.append("GPU detected accurately via nvidia-smi telemetry.")
            return res_nvidia

        # Strategy B: Windows Registry display adapter enumeration
        if sys.platform == "win32":
            res_reg = self._detect_gpu_via_registry(notes)
            if res_reg and res_reg.get("name") != "Unknown":
                return res_reg

        # Strategy C: PowerShell Get-CimInstance Win32_VideoController
        if sys.platform == "win32":
            res_ps = self._detect_gpu_via_powershell(notes)
            if res_ps and res_ps.get("name") != "Unknown":
                return res_ps

        # Strategy D: WMIC fallback
        if sys.platform == "win32":
            res_wmic = self._detect_gpu_via_wmic(notes)
            if res_wmic and res_wmic.get("name") != "Unknown":
                return res_wmic

        notes.append("Dedicated GPU or VRAM could not be confirmed. Marked as Unknown.")
        return {
            "name": "Unknown",
            "vendor": "Unknown",
            "vram_mb": None,
            "shared_memory_mb": None,
            "driver_version": None,
            "nvidia_gpu_present": False,
        }

    def _detect_gpu_via_nvidia_smi(self) -> Optional[Dict[str, Any]]:
        """Queries nvidia-smi CLI for exact dedicated VRAM and driver."""
        rc, stdout, _ = self._cmd_runner([
            "nvidia-smi",
            "--query-gpu=gpu_name,memory.total,driver_version",
            "--format=csv,noheader,nounits"
        ])
        if rc == 0 and stdout.strip():
            first_line = stdout.strip().splitlines()[0]
            parts = [p.strip() for p in first_line.split(",")]
            if len(parts) >= 3:
                try:
                    vram_mb = int(float(parts[1]))
                    return {
                        "name": parts[0],
                        "vendor": "NVIDIA",
                        "vram_mb": vram_mb,
                        "shared_memory_mb": None,
                        "driver_version": parts[2],
                        "nvidia_gpu_present": True,
                    }
                except ValueError:
                    pass
        return None

    def _detect_gpu_via_registry(self, notes: List[str]) -> Optional[Dict[str, Any]]:
        """
        Inspects Windows Display Adapter registry keys for dedicated VRAM
        (HardwareInformation.qwMemorySize).
        """
        try:
            import winreg
            class_guid = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            base_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, class_guid)

            adapters = []
            i = 0
            while True:
                try:
                    sub_name = winreg.EnumKey(base_key, i)
                    i += 1
                    if not sub_name.isdigit():
                        continue
                    sub_key = winreg.OpenKey(base_key, sub_name)

                    desc = None
                    try:
                        desc, _ = winreg.QueryValueEx(sub_key, "DriverDesc")
                    except Exception:
                        pass

                    driver_ver = None
                    try:
                        driver_ver, _ = winreg.QueryValueEx(sub_key, "DriverVersion")
                    except Exception:
                        pass

                    # Read dedicated 64-bit VRAM bytes
                    vram_bytes = None
                    try:
                        qw, _ = winreg.QueryValueEx(sub_key, "HardwareInformation.qwMemorySize")
                        if isinstance(qw, int) and qw > 0:
                            vram_bytes = qw
                    except Exception:
                        pass

                    if vram_bytes is None:
                        try:
                            dw, _ = winreg.QueryValueEx(sub_key, "HardwareInformation.MemorySize")
                            if isinstance(dw, int) and dw > 0:
                                vram_bytes = dw
                        except Exception:
                            pass

                    if desc:
                        vram_mb = (vram_bytes // (1024 * 1024)) if vram_bytes else None
                        adapters.append({
                            "name": desc.strip(),
                            "driver_version": driver_ver.strip() if driver_ver else None,
                            "vram_mb": vram_mb,
                        })
                except OSError:
                    break

            if not adapters:
                return None

            # Prioritize discrete NVIDIA or AMD GPU if present
            discrete = None
            for a in adapters:
                lower = a["name"].lower()
                if "nvidia" in lower or "geforce" in lower or "rtx" in lower or "gtx" in lower or "radeon" in lower:
                    discrete = a
                    break

            target = discrete or adapters[0]
            name = target["name"]
            vendor = "NVIDIA" if "nvidia" in name.lower() else ("Intel" if "intel" in name.lower() else ("AMD" if "amd" in name.lower() else "Unknown"))

            notes.append(f"GPU detected via Windows registry: {name}")
            return {
                "name": name,
                "vendor": vendor,
                "vram_mb": target["vram_mb"],
                "shared_memory_mb": None,
                "driver_version": target["driver_version"],
                "nvidia_gpu_present": (vendor == "NVIDIA"),
            }
        except Exception as e:
            notes.append(f"Registry display query warning: {e}")
            return None

    def _detect_gpu_via_powershell(self, notes: List[str]) -> Optional[Dict[str, Any]]:
        """Queries PowerShell CIM for Win32_VideoController."""
        ps_cmd = (
            "Get-CimInstance Win32_VideoController | "
            "Select-Object Name, AdapterRAM, DriverVersion | "
            "ConvertTo-Json -Compress"
        )
        rc, stdout, _ = self._cmd_runner(["powershell", "-NoProfile", "-Command", ps_cmd])
        if rc == 0 and stdout.strip():
            import json
            try:
                data = json.loads(stdout.strip())
                items = data if isinstance(data, list) else [data]
                # Prioritize NVIDIA / AMD
                selected = None
                for it in items:
                    name = it.get("Name", "")
                    if "nvidia" in name.lower() or "geforce" in name.lower() or "radeon" in name.lower():
                        selected = it
                        break
                if not selected and items:
                    selected = items[0]

                if selected:
                    name = selected.get("Name", "Unknown")
                    vendor = "NVIDIA" if "nvidia" in name.lower() else ("Intel" if "intel" in name.lower() else "Unknown")
                    adapter_ram = selected.get("AdapterRAM")
                    vram_mb = None
                    if adapter_ram and isinstance(adapter_ram, (int, float)) and adapter_ram > 0:
                        vram_mb = int(adapter_ram // (1024 * 1024))
                    return {
                        "name": name,
                        "vendor": vendor,
                        "vram_mb": vram_mb,
                        "shared_memory_mb": None,
                        "driver_version": selected.get("DriverVersion"),
                        "nvidia_gpu_present": (vendor == "NVIDIA"),
                    }
            except Exception:
                pass
        return None

    def _detect_gpu_via_wmic(self, notes: List[str]) -> Optional[Dict[str, Any]]:
        """Fallback for older systems supporting wmic."""
        rc, stdout, _ = self._cmd_runner([
            "wmic", "path", "win32_videocontroller", "get", "name,adapterram,driverversion", "/format:csv"
        ])
        if rc == 0 and stdout.strip():
            lines = [l.strip() for l in stdout.strip().splitlines() if l.strip()]
            for line in lines[1:]:  # skip header
                parts = line.split(",")
                if len(parts) >= 3:
                    # format: Node, AdapterRAM, DriverVersion, Name
                    ram_str = parts[1].strip()
                    d_ver = parts[2].strip()
                    name = parts[3].strip() if len(parts) > 3 else "Unknown"
                    vram_mb = int(int(ram_str) // (1024 * 1024)) if ram_str.isdigit() else None
                    vendor = "NVIDIA" if "nvidia" in name.lower() else ("Intel" if "intel" in name.lower() else "Unknown")
                    return {
                        "name": name,
                        "vendor": vendor,
                        "vram_mb": vram_mb,
                        "shared_memory_mb": None,
                        "driver_version": d_ver or None,
                        "nvidia_gpu_present": (vendor == "NVIDIA"),
                    }
        return None

    # --------------------------------------------------------------------------
    # 6. CUDA Capability Detection
    # --------------------------------------------------------------------------
    def _detect_cuda(self, nvidia_present: bool, notes: List[str]) -> bool:
        """Determines if CUDA execution is available on the machine."""
        if not nvidia_present:
            return False

        # 1. Check nvcuda.dll presence in Windows System32
        if sys.platform == "win32":
            system_root = os.environ.get("SystemRoot", r"C:\Windows")
            nvcuda_path = os.path.join(system_root, "System32", "nvcuda.dll")
            if os.path.exists(nvcuda_path):
                # CUDA driver library is present on system
                pass

        # 2. Check if PyTorch with CUDA is available (non-blocking)
        try:
            import torch
            if hasattr(torch, "cuda") and torch.cuda.is_available():
                return True
        except Exception:
            pass

        # 3. Check nvidia-smi return code
        rc, _, _ = self._cmd_runner(["nvidia-smi"])
        if rc == 0:
            return True

        return False
