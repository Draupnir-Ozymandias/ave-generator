from copy import deepcopy

from ave_light_renderer.canonical import load_json
from ave_light_renderer.validation import _jsonschema_validate

from .errors import ProtocolValidationError
from .paths import PROTOCOL_SCHEMA_PATH


def validate_protocol(protocol: dict) -> dict:
    schema = load_json(PROTOCOL_SCHEMA_PATH)
    try:
        _jsonschema_validate(protocol, schema, PROTOCOL_SCHEMA_PATH)
    except Exception as exc:
        raise ProtocolValidationError(str(exc)) from exc

    sample_rate = protocol["sample_rate_hz"]
    exact_sample_count = protocol["duration_seconds"] * sample_rate
    if abs(exact_sample_count - round(exact_sample_count)) > 1e-9:
        raise ProtocolValidationError("duration_seconds must resolve to an integer sample count")
    nyquist = sample_rate / 2
    synthesis = protocol["synthesis"]
    sweep = synthesis["sweep"]
    if sweep["end_hz"] <= sweep["start_hz"]:
        raise ProtocolValidationError("sweep end_hz must be greater than start_hz")
    carrier = synthesis["carrier_hz"]
    partial_multiples = [item["multiple"] for item in synthesis["harmonics"]]
    if len(partial_multiples) != len(set(partial_multiples)):
        raise ProtocolValidationError("harmonic multiples must be unique")
    if partial_multiples.count(1) != 1:
        raise ProtocolValidationError("harmonics must declare exactly one fundamental")
    highest_partial = max(partial_multiples)
    if carrier * highest_partial >= nyquist:
        raise ProtocolValidationError("highest carrier partial must remain below Nyquist")
    if carrier + synthesis["binaural"]["max_difference_hz"] >= nyquist:
        raise ProtocolValidationError("right-channel fundamental must remain below Nyquist")

    transition = synthesis["transition_bands_hz"]
    if not (
        transition["binaural_to_isochronic"][0]
        < transition["binaural_to_isochronic"][1]
        < transition["isochronic_to_harmonic"][0]
        < transition["isochronic_to_harmonic"][1]
        <= synthesis["sweep"]["end_hz"]
    ):
        raise ProtocolValidationError("transition bands must be strictly ordered within the sweep")
    if protocol["output"]["fade_seconds"] * 2 > protocol["duration_seconds"]:
        raise ProtocolValidationError("fade_seconds cannot consume more than the full duration")
    return deepcopy(protocol)
