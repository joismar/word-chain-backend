def calculate_score(left_word: str, right_word: str):
    scored = False
    for score_level in 7, 6, 5, 4, 3, 2, 1:
        if len(left_word) < score_level or len(right_word) < score_level:
            continue

        user_sliced_word = left_word[-score_level:]
        last_game_sliced_word = right_word[:score_level]

        if user_sliced_word == last_game_sliced_word:
            scored = True
            return score_level

    if not scored:
        return 0