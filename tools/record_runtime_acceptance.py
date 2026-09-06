"""Validate event provenance; never infer visual correctness or hardware success.

Defaults identify the historical development fixture used by the inherited
tests, not the current release. Pass expected_rom and expected_core explicitly
when validating a current run. Private recordings are never included here.
"""
ROM_SHA256 = "b788876eb7e003597740dd1195a286baeca342cba270dbf226145e635ae05113"
CORE_SHA256 = "0d3177c927d791fef897f735d88db3646f7932d02054af108619c6df4e1597f1"

def validate_run(events, expected_input, *, clean, expected_rom=ROM_SHA256,
                 expected_core=CORE_SHA256):
    if not events or events[0].get("op") != "initialize":
        raise ValueError("Missing initialization evidence")
    initial = events[0]
    for key, expected in (("rom_sha256", expected_rom), ("core_sha256", expected_core),
                          ("input_save_sha256", expected_input)):
        if initial.get(key) != expected:
            raise ValueError(f"Run is not bound to the required {key}")
    if initial.get("frame") != 0 or initial.get("ram_interventions") != 0:
        raise ValueError("A cold run must begin at frame zero without interventions")
    requests = [event.get("request", {}) for event in events[1:]]
    if not requests or requests[-1].get("op") != "close":
        raise ValueError("No normal close at the end of the recorded run")
    if any(event.get("op") == "initialize" for event in events[1:]):
        raise ValueError("Multiple initializations in one evidence run")
    if clean and any(request.get("op") in ("write_ram", "state_load") for request in requests):
        # State-load metadata alone cannot prove absence of earlier fixture RAM.
        raise ValueError("RAM/state intervention invalidates clean progression evidence")
    allowed = {"frames", "screenshot", "read", "dump", "state_save", "save_export", "close"}
    if clean and any(request.get("op") not in allowed for request in requests):
        raise ValueError("Unknown operation in clean progression chain")
    if clean and any(events[i]["frame"] > events[i+1]["frame"] for i in range(len(events)-1)):
        raise ValueError("Frame rewind in clean progression chain")
    if any(request.get("op") == "close" for request in requests[:-1]):
        raise ValueError("Operations recorded after close")
    exports = [event for event in events if event.get("request", {}).get("op") == "save_export"]
    for event in exports:
        result = event.get("result", {})
        if result.get("size") != 8192 or (clean and result.get("fixture_modified") is not False):
            raise ValueError("Save size/fixture classification is not acceptable")
    return {"cold_input_save_sha256": expected_input,
            "frames": events[-1]["frame"], "normal_close": True,
            "ram_writes": sum(request.get("op") == "write_ram" for request in requests),
            "state_loads": sum(request.get("op") == "state_load" for request in requests),
            "clean_progression": clean, "save_exports": len(exports)}
