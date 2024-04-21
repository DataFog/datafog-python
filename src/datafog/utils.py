def get_json_shape(json_data: dict) -> str:
    if isinstance(json_data, dict):
        return f"Root is a dictionary with {len(json_data)} keys."
    elif isinstance(json_data, list):
        return f"Root is a list with {len(json_data)} elements."
    else:
        return "Root is neither a dictionary nor a list."
