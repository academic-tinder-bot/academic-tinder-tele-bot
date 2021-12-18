import csv
import random

# Names gotten from r/namenerds nursery 2021
# https://www.reddit.com/r/namenerds/wiki/index/nursery

with open('src/utils/name_list.csv') as csv_file:
 
    # creating an object of csv reader
    # with the delimiter as ,
    csv_reader = csv.reader(csv_file, delimiter = ',')

    list_of_first_names = [name[0].split(" ")[0] for name in list(csv_reader)]

def randomAnonName() -> str:
    return "Anon " + random.choice(list_of_first_names)