import os


def change_extension(file_path:str, ext=".txt"):

    # Get filename without extension
    base = os.path.splitext(file_path)[0]

    # New file name with given extension
    new_file = base + ext
    os.rename(file_path, new_file)
    print(file_path, "is renamed to:", new_file)
    return new_file


if __name__ =="__main__":
    change_extension("helpers/gemini.txt",".py")