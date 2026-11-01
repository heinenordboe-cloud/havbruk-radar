# Størrelse og sha256 for det som ble drept ved minnegrensa på kystvakt-1.
import hashlib, json, lzma, sys, time
from compression import zstd
from pathlib import Path
Z = zstd.CompressionParameter
for p in sys.argv[1:]:
    raa = zstd.decompress(Path(p).read_bytes())
    fasit = hashlib.sha256(raa).hexdigest()
    t0 = time.process_time()
    l = zstd.compress(raa, options={Z.compression_level: 19, Z.window_log: 27, Z.enable_long_distance_matching: True})
    t1 = time.process_time()
    x = lzma.compress(raa, preset=9)
    t2 = time.process_time()
    print(json.dumps({"time": Path(p).name, "lagret": Path(p).stat().st_size, "raa": len(raa),
        "zstd19_long27": len(l), "zstd_lik": hashlib.sha256(zstd.decompress(l)).hexdigest() == fasit, "zstd_cpu_mac": round(t1-t0, 1),
        "xz9": len(x), "xz_lik": hashlib.sha256(lzma.decompress(x)).hexdigest() == fasit, "xz_cpu_mac": round(t2-t1, 1)}), flush=True)
