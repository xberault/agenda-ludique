import json
import os
from concurrent.futures.thread import ThreadPoolExecutor

import requests
import yaml
from bs4 import BeautifulSoup

domain = "https://boardgamegeek.com"
main_url = "https://boardgamegeek.com/browse/boardgame/page/"
cover_url = "https://api.geekdo.com/api/images/"
i = 1


# yaml Structure
#     140620: <-- int (id)
#       title: str
#       publication_year: int
#       min_players: int
#       max_players: int
#       min_playtime: int
#       images:
#         micro: str (url)
#         small: str (url)
#         medium: str (url)
#         large: str (url)
#         square: str (url)
#         expanded: str (url)
#         crop_100: str (url)
#         square_200: str (url)
#         original: str (url)
#       rank: id


def get_cover(image_id):
    try:
        json_file = requests.get(cover_url + str(image_id)).json()['images']
    except TypeError:  # If we can get the webpage we got a None type and so raise a TypeError exception
        return None
    if "pic1657689" in json_file["original"]["url"]:
        return None
    return {
        "micro": json_file["micro"]["url"],
        "small": json_file["small"]["url"],
        "medium": json_file["medium"]["url"],
        "large": json_file["large"]["url"],
        "square": json_file["square"]["url"],
        "expanded": json_file["expanded"]["url"],
        "crop_100": json_file["crop100"]["url"],
        "square_200": json_file["square200"]["url"],
        "original": json_file["original"]["url"]
    }


def get_game_info(url):
    raw_html = BeautifulSoup(  # Get raw html of domain + url
        requests.get(domain + url).text,
        "html.parser"
    )
    a = map(str, raw_html.find_all('script'))  # Transform it to an Iterator[str]
    json_text = None
    for elem in a:  # For each <script>
        if 'GEEK.geekitemPreload' in elem:  # if we got the infos
            temp = elem.split('GEEK.geekitemPreload = ')[1]  # Get rid of previous code
            temp2 = temp.split('};', 1)[0]  # Get rid of useless code after the JSON file
            temp2 = temp2 + '}'  # Restore the '}' we removed the line before
            json_text = json.loads(temp2)['item']  # Transform dirty string into proper JSON format
    covers = get_cover(json_text["imageid"])
    if covers is None:
        return None
    return {
        "title": json_text["name"],
        "publication_year": int(json_text["yearpublished"]),
        "min_players": int(json_text["minplayers"]),
        "max_players": int(json_text["maxplayers"]),
        "min_playtime": int(json_text["minplaytime"]),
        "average_rating": float(json_text["stats"]["average"]),
        "images": covers
    }


def create_game_list(raw_html):
    game_list_dict = {}
    global i
    for game in map(str, raw_html.find_all("a", {"class": "primary"})):  # This way we can iterate and parse html
        game = BeautifulSoup(game, "html.parser")  # Convert str into bs4 object
        href = game.find('a')['href']  # extract href content
        id_game = int(href.split('/')[2])  # extract id from href content
        game_info = get_game_info(href)  # Get game info into dict
        if game_info is not None:  # Check if we have game info, if not skip this game
            game_list_dict[id_game] = game_info  # Transfer game info into the big ass dict
            game_list_dict[id_game]["rank"] = i  # Add rank to save order
            print(f"Jeu n⁰{i}: {game_list_dict[id_game]['title']}")  # Just to inform where the program is
            i += 1
        else:
            print("Informations manquantes pour ce jeu, skipping...")
    return game_list_dict


def save_yaml(game_list_dict):
    with open('games-data.yaml', 'a') as f:
        f.write(yaml.dump(game_list_dict, sort_keys=False))  # write game_list_dict to the file and disable auto sort


def sub_main(j):
    main_html = BeautifulSoup(  # Request raw page and make a bs4 object
        requests.get(main_url + str(j)).text,
        "html.parser"
    )
    game_list_dict = create_game_list(main_html)
    print("Sauvegarde dans le fichier yaml en cours...")
    save_yaml(game_list_dict)  # Save yaml into games-data.yaml
    print("Fini !")


def main():
    from_page = input("Scrap de la page : ")  # Get first page to scrape
    to_page = input("Jusqu'à la page : ")  # Get last page to scrape

    try:
        os.remove("games-data.yaml")
        print("Ancien game-data.yaml supprimé")
    except FileNotFoundError:
        print("Création de game-data.yaml")

    with ThreadPoolExecutor(max_workers=int(to_page)) as executor:  # Overkill but it's faster :)
        for j in range(int(from_page), int(to_page) + 1):  # to_page + 1 bc its [from_page ; to_page[
            executor.submit(sub_main, j)


if __name__ == '__main__':
    main()
