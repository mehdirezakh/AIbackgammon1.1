my_var = 10

def test_func():
    global my_var
    my_var = 20
    print("Inside function:", my_var)

if __name__ == "__main__":

    print("Before in main:", my_var)
    my_var = 30
    print("After in main:", my_var)
    test_func()
    print("After function call in main:", my_var)