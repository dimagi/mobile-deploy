
# String Boolean -> Boolean
def prompt_until_answer(msg, is_first_prompting):
    if is_first_prompting:
        to_proceed = input(msg)
    else:
        to_proceed = input("Please answer with 'y' or 'n'")
    if to_proceed == '' or to_proceed.lower() == 'y':
        return True
    elif to_proceed.lower() == 'n':
        return False
    return prompt_until_answer(msg, false)

# String String -> None
def verify_value_with_user(verify_msg, exit_msg):
    if not prompt_until_answer(verify_msg):
        print(exit_msg)
        exit(0)

