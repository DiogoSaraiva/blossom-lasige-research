def dance_sequence_from_data(tempo:float, energy:float) -> str:
    if tempo > 100 and energy > 0.1:
        sequence = "happy"
    else:
        sequence = "sad"

    return sequence