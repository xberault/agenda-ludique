import json
import time
import click
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from app import db
from app.utils.scraper import RewriteScraper
from app.utils.insert_db import insertDB

from app.models import User, Game, BookmarkUser, HideUser, Note, Wish, KnowRules, Collect, Prefer, Group, Participate, \
    Genre, Classification, Session, TimeSlot, Play, Use
from . import admin_blueprint


@admin_blueprint.cli.command('resetDB')
def reset_db():
    """ Clear all the data of the database """
    for table in reversed(db.metadata.sorted_tables):
        print(f'Clear table {table}')
        db.session.execute(table.delete())
    db.session.commit()


@admin_blueprint.cli.command('loaddb_games')
@click.argument('filename')
def loaddb_games(filename):
    """ Populates the database with games from a yml file """
    games = yaml.safe_load(open(filename))

    deb = time.perf_counter()
    # creation d'un profil BGG
    bgg = User.from_username("BGG")
    if bgg is None:
        bgg = User(
            email="mmm.dupuis45@gmail.com",
            username="BGG",
            first_name="Board Game",
            last_name="Geek",
            password="BGGdu45",
            profile_picture="https://cf.geekdo-static.com/images/logos/navbar-logo-bgg-b2.svg")
        db.session.add(bgg)
        db.session.commit()
    bgg_id = bgg.id

    # premier tour de boucle, creation des jeux et des genres
    nb_jeux_rejetes = 0
    for title, game in games.items():
        if len(title) <= 128 and Game.from_title(title) is None:
            game_object = Game(
                title=game["title"],
                publication_year=game["publication_year"],
                min_players=game["min_players"],
                max_players=game["max_players"],
                min_playtime=game["min_playtime"],
                image=game["images"]["original"])
            db.session.add(game_object)
            print("V", title)
        else:
            print("X", title)
            nb_jeux_rejetes += 1
        for typ in game["type"]:  # creation des genres
            if Genre.from_name(typ) is None:
                genre_object = Genre(name=typ)
                db.session.add(genre_object)
    db.session.commit()

    # deuxieme tour de boucle pour les notes de bgg et les genres du jeu
    for title, game in games.items():
        g = Game.from_title(title)
        if g != None:
            g_id = g.id
            if Note.from_both_ids(bgg_id, g_id) is None:
                rating = Note(
                    note=round(game["average_rating"]),
                    message="Auto-generated note, the average rating of the game at boardgamegeek.com",
                    user_id=bgg_id,
                    game_id=g_id)
                db.session.add(rating)
                print("V", Note, title)
            else:
                print("X", Note, title)

            for typ in game["type"]:
                genre_id = Genre.from_name(typ).id
                if Classification.from_both_ids(g_id, genre_id) is None:
                    classification = Classification(game_id=g_id, genre_id=genre_id)
                    db.session.add(classification)

    db.session.commit()

    print("Nombre de jeux rejet??s : ", nb_jeux_rejetes)
    print(f"Temps d'ex??cutuion : {time.perf_counter() - deb:0.4f} sec")


@admin_blueprint.cli.command('fast_loaddb_games')
@click.argument('filename')
def fast_loaddb_games(filename):
    """ WARNING ! ONLY WITH AN EMPTY DATABASE ! Populates the database with games from a yml file """
    print("Chargement du fichier yaml en memoire")
    games = yaml.safe_load(open(filename))

    deb = time.perf_counter()
    # creation d'un profil BGG
    bgg = User(
        email="mmm.dupuis45@gmail.com",
        username="BGG",
        first_name="Board Game",
        last_name="Geek",
        password="BGGdu45",
        profile_picture="https://cf.geekdo-static.com/images/logos/navbar-logo-bgg-b2.svg")
    db.session.add(bgg)
    db.session.commit()
    bgg_id = bgg.id

    print("Premier tour de boucle...")
    # premier tour de boucle, creation des jeux et des genres
    dico_games = dict()  # {game.title: game}
    i = 0
    for title, game in games.items():
        if len(title) > 128 or '??' in game["title"]:  # Continue la boucle et ignore le reste
            continue
        game_object = Game(
            title=game["title"],
            publication_year=game["publication_year"],
            min_players=game["min_players"],
            max_players=game["max_players"],
            min_playtime=game["min_playtime"],
            image=game["images"]["original"])
        db.session.add(game_object)
        print("V", title)
        dico_games[title] = game_object
        for typ in game["type"]:  # creation des genres
            if Genre.from_name(typ) is None:
                game_object = Genre(name=typ)
                db.session.add(game_object)
        i += 1
        if i % 100 == 0:
            print(f"{i} jeux insere")
    db.session.commit()

    print("Deuxieme tour de boucle...")
    # deuxieme tour de boucle pour les notes de bgg et les genres du jeu
    default_message = "Auto-generated note, the average rating of the game at boardgamegeek.com"
    i = 0
    for title, game in games.items():
        if '??' in game["title"]:
            continue
        g_id = dico_games[title].id
        rating = Note(
            note=round(game["average_rating"]),
            message=default_message,
            user_id=bgg_id,
            game_id=g_id)
        db.session.add(rating)

        for typ in game["type"]:
            genre_id = Genre.from_name(typ).id
            classification = Classification(game_id=g_id, genre_id=genre_id)
            db.session.add(classification)
    db.session.commit()

    print(f"Temps d'ex??cutuion : {time.perf_counter() - deb:0.4f} sec")


@admin_blueprint.cli.command('scraper')
def scraper():
    print("!!! PENSEZ ?? VIDER LA BD POUR ??VITER LES CONFLITS !!!")
    choice = input("  1) Scraper\n  2) JSON\n")

    data = None
    if choice == "1":
        from_page = input("Scrap de la page : ")
        to_page = input("Jusqu'?? la page : ")
        rs = RewriteScraper()
        data = rs.scrap(from_page, to_page)
        with open("ressources/data.json", 'w') as f:
            json.dump(data, f)
        print("Donn??es sauvegard?? dans ressources/data.json")
    elif choice == "2":
        with open("ressources/data.json", 'r') as f:
            data = json.load(f)
        print("Chargement en m??moire termin??")
    else:
        exit(1)

    print("Insertion dans la BDD en cours...")
    iDB = insertDB()
    iDB.insert(data)
    print("Done!")


def load_relationship(yml, kw_id, object_id, keyword_yml, rs, get_id, kw, list_kwsup=[], get_id_kw=""):
    """
    Create a relationship and add it to the current session.
    :param yml: a yml dict which represent the first object of the relationship
    :param kw_id: the first keyword argument of the relationship (eg: 'user_id')
    :param object_id: the id of the first object of the relationship (eg: 54)
    :param keyword_yml: the keyword that determines which part of the yml will be added (eg: 'preferences')
    :param rs: the relationship class (eg: Prefer)
    :param get_id: the method used to get the id of the second object of the relationship (eg: Game.from_title)
    :param kw: the second keyword argument of the relationship (eg: 'game_id')
    :param list_kwsup: list of additional keyword arguments (eg: ['frequency'])
    :param get_id_kw: the keyword that determines which part of the yml the get_id method uses as an argument
    """
    for elem in yml[keyword_yml]:
        if get_id_kw:
            elem_id = get_id(elem[get_id_kw]).id
        else:
            elem_id = get_id(elem).id
        if rs.from_both_ids(**{kw_id: object_id}, **{kw: elem_id}) is None:
            dico_kwsup = dict()
            for kwsup in list_kwsup:
                dico_kwsup[kwsup] = elem[kwsup]
            rs_object = rs(**{kw_id: object_id}, **{kw: elem_id}, **dico_kwsup)
            db.session.add(rs_object)
            print("V", rs, object_id, elem_id)
        else:
            print("X", rs, object_id, elem_id)


@admin_blueprint.cli.command('loaddb_users')
@click.argument('filename')
def loaddb_users(filename):
    """ Populates the database with users and user-related relationships from a yml file. Requires loaddb_games. """
    users = yaml.safe_load(open(filename))

    # premier tour de boucle, creation des users
    for u in users:
        if User.from_username(u["username"]) == None:
            user_object = User(
                email=u["email"],
                username=u["username"],
                first_name=u["first_name"],
                last_name=u["last_name"],
                password=u["password"],
                profile_picture=u["profile_picture"])
            db.session.add(user_object)
            print("V", u["username"])
        else:
            print("X", u["username"])
    db.session.commit()

    # deuxieme tour de boucle, creation des relations UserXGame et UserXUser
    for u in users:
        u_id = User.from_username(u["username"]).id  # existe forcement
        kw_id = 'user_id'
        relations_uxu = {"bookmarked_users": BookmarkUser, "hidden_users": HideUser}
        relations_uxg = {"wishes": Wish, "known": KnowRules, "collection": Collect}

        for kw_yml, rs in relations_uxu.items():
            load_relationship(u, kw_id, u_id, kw_yml, rs, User.from_username, 'user2_id')
        get_id = Game.from_title
        kw = 'game_id'
        for kw_yml, rs in relations_uxg.items():
            load_relationship(u, kw_id, u_id, kw_yml, rs, get_id, kw)
        get_id_kw = 'title'
        load_relationship(u, kw_id, u_id, 'preferences', Prefer, get_id, kw, ['frequency'], get_id_kw)
        load_relationship(u, kw_id, u_id, 'notes', Note, get_id, kw, ['note', 'message'], get_id_kw)
    db.session.commit()


@admin_blueprint.cli.command('loaddb_groups')
@click.argument('filename')
def loaddb_groups(filename):
    """ Populates the database with groups and group-related relationships from a yml file. Requires loaddb_users. """
    groups = yaml.safe_load(open(filename))

    # premier tour de boucle, creation des groupes
    for g in groups:
        if Group.from_name(g["name"]) is None:
            group_object = Group(
                name=g["name"],
                is_private=g["is_private"],
                password=g["password"],
                manager_id=User.from_username(g["manager"]).id)
            db.session.add(group_object)
            print("V", g["name"])
        else:
            print("X", g["name"])
    db.session.commit()

    # deuxieme tour de boucle, creation des relations UserXGroup
    for g in groups:
        g_id = Group.from_name(g["name"]).id
        load_relationship(g, 'group_id', g_id, 'members', Participate, User.from_username, 'member_id')
    db.session.commit()


@admin_blueprint.cli.command('loaddb_sessions')
@click.argument('filename')
def loaddb_sessions(filename):
    """ Populates the database with sessions and session-related relationships from a yml file. Requires loaddb_games and loaddb_users """
    sessions = yaml.safe_load(open(filename))

    # premier tour de boucle, creation des sessions et des timeslots
    dico_timeslots = dict()  # k=session_yml_id, v=timeslot_object
    dico_sessions = dict()  # k=session_yml_id, v=session_object
    for id, s in sessions.items():
        session_object = Session(
            nb_players_required=s["nb_players_required"],
            notifactions_sent=s["notifactions_sent"],
            confirmed=s["confirmed"],
            timeout=s["timeout"],
            archived=s["archived"])
        db.session.add(session_object)
        dico_sessions[id] = session_object

        timeslot = s["timeslot"]
        timeslot_object = TimeSlot(
            beginning=timeslot["beginning"],
            end=timeslot["end"],
            day=timeslot["day"])
        db.session.add(timeslot_object)
        dico_timeslots[id] = timeslot_object
    db.session.commit()

    # deuxieme tour de boucle, ajout des relations SessionXTimeslot, SessionXGame et SessionXUser
    for id, s in sessions.items():
        session_object = dico_sessions[id]
        session_object.timeslot_id = dico_timeslots[id].id
        load_relationship(s, 'session_id', session_object.id, 'games', Use, Game.from_title, 'game_id',
                          ['expected_time'], 'title')
        load_relationship(s, 'session_id', session_object.id, 'players', Play, User.from_username, 'user_id',
                          ['confirmed', 'won'], 'username')
    db.session.commit()
