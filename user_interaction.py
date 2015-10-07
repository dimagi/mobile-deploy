import sys


# String Boolean -> Boolean
def prompt_until_answer(msg, is_first_prompting):
    yn_msg = '{} ([y]/n)'.format(msg)
    if is_first_prompting:
        to_proceed = input(yn_msg)
    else:
        to_proceed = input("Please answer with 'y' or 'n'")
    if to_proceed == '' or to_proceed.lower() == 'y':
        return True
    elif to_proceed.lower() == 'n':
        return False
    return prompt_until_answer(msg, False)


# String String -> None
def verify_value_with_user(verify_msg, exit_msg):
    if not prompt_until_answer(verify_msg, True):
        print(exit_msg)
        sys.exit(0)


# String Boolean [String -> Boolean] -> String
def prompt_user_with_validation(msg, is_first_prompting, validation_func):
    if is_first_prompting:
        user_response = input(msg)
    else:
        user_response = input("Invalid answer, try again")

    if validation_func(user_response):
        return user_response
    return prompt_until_answer(msg, False, validation_func)
