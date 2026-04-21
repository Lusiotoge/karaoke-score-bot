import db

def process_exp(user, score_diff):
    if score_diff <= 0:
        return None

    exp = int(score_diff * 10)

    before_exp, before_level = db.get_level(user)
    total_exp, level = db.add_exp(user, exp)

    leveled_up = level > before_level

    return exp, total_exp, level, leveled_up