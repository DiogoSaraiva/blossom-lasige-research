def dance_sequence_from_data(tempo: float, energy: float) -> str:
    """
    Decide which dance sequence to use based on tempo and energy.
    Available sequences: happy, sad, anger, fear, yes, no
    """

    if tempo > 140 and energy > 0.07:
        sequence = "anger"   # fast & high energy -> anger
    elif tempo > 120 and energy > 0.05:
        sequence = "happy"   # upbeat -> happy
    elif tempo < 90 and energy < 0.03:
        sequence = "fear"    # very slow & low energy -> fear
    elif 90 <= tempo <= 120 and 0.03 <= energy <= 0.05:
        sequence = "sad"     # medium-slow with low energy -> sad
    elif 100 <= tempo <= 130 and energy > 0.06:
        sequence = "yes"     # rhythmic & medium-fast -> yes
    elif 80 <= tempo <= 110 and energy > 0.04:
        sequence = "no"      # slower but with bursts of energy -> no
    else:
        sequence = "sad"     # fallback (default to sad)

    return sequence