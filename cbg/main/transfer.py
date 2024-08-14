from .models import *
from django.db.models import Sum
from django.utils import timezone
from django.db.models import Q
import sqlite3

def transfer_scores():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT golfer, hole, score, week, year from main_score")

    # loop through each score object
    for row in cursor:

        # get data from score object
        golfer = row[0]
        hole = row[1]
        score = row[2]
        week = row[3]
        year = row[4]

        print(golfer)
        print(hole)
        print(score)
        print(week)
        print(year)

        # get golfer name from ID
        for row in conn_old.execute(f'SELECT name from main_golfer WHERE id = {golfer}'):
            print(row)
            golfer_name = row[0]

        print(golfer_name)

        # get new DB items
        season = Season.objects.get(year=int(year))
        golfer = Golfer.objects.get(name=golfer_name)
        week = Week.objects.get(season=season, number=int(week))
        hole = Hole.objects.get(season=season, number=int(hole))

        score = Score(golfer=golfer, week=week, hole=hole, score=int(score))

        score.save()


def transfer_teams():
    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT name, team, year from main_golfer")

    # loop through each score object
    for row in cursor:

        # get data from score object
        name = row[0]
        team = int(row[1])
        year = int(row[2])

        print(name)
        print(team)
        print(year)

        if year == 2019 and team != 0:
            team_obj = Team.objects.get(id=team)
            golfer = Golfer.objects.get(name=name)

            team_obj.golfers.add(golfer)
            team_obj.save()
        if year == 2020 and team != 0:
            team_obj = Team.objects.get(id=team+8)
            golfer = Golfer.objects.get(name=name)

            team_obj.golfers.add(golfer)
            team_obj.save()
        if year == 2021 and team != 0:
            team_obj = Team.objects.get(id=team+16)
            golfer = Golfer.objects.get(name=name)

            team_obj.golfers.add(golfer)
            team_obj.save()
        if year == 2022 and team != 0:
            team_obj = Team.objects.get(id=team+26)
            golfer = Golfer.objects.get(name=name)

            team_obj.golfers.add(golfer)
            team_obj.save()

def transfer_matchup():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT week, team1, team2, year, front from main_matchup")

    # loop through each score object
    for row in cursor:

        # get data from score object
        week = int(row[0])
        team1 = int(row[1])
        team2 = int(row[2])
        year = int(row[3])
        is_front = bool(row[4])

        print(week)
        print(year)
        print(team1)
        print(team2)
        print(is_front)

        # adjust the team number to work with the new DB ID.
        if year == 2019:
            team1 = team1
            team2 = team2
        elif year == 2020:
            team1 = team1 + 8
            team2 = team2 + 8
        elif year == 2021:
            team1 = team1 + 16
            team2 = team2 + 16
        elif year == 2022:
            team1 = team1 + 26
            team2 = team2 + 26

        season = Season.objects.get(year=year)
        week = Week.objects.get(number=week, season=season, rained_out=False)

        week.is_front = is_front
        week.save()

        matchup = Matchup(week=week)

        team1 = Team.objects.get(id=team1)
        team2 = Team.objects.get(id=team2)

        matchup.save()

        matchup.teams.add(team1, team2)


def transfer_subs():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT week, year, absent_id, sub_id from main_subrecord")

    # loop through each score object
    for row in cursor:

        # get data from score object
        week = int(row[0])
        year = int(row[1])
        absent_id = int(row[2])
        sub_id = int(row[3])

        print(week)
        print(year)
        print(absent_id)
        print(sub_id)

        season = Season.objects.get(year=year)
        week = Week.objects.get(number=week, season=season, rained_out=False)

        # get golfer name from ID
        for row in conn_old.execute(f'SELECT name from main_golfer WHERE id = {absent_id}'):
            print(row)
            absent_name = row[0]

        # get golfer name from ID
        for row in conn_old.execute(f'SELECT name from main_golfer WHERE id = {sub_id}'):
            print(row)
            sub_name = row[0]

        absent = Golfer.objects.get(name=absent_name)
        sub = Golfer.objects.get(name=sub_name)

        sub = Sub(absent_golfer=absent, sub_golfer=sub, week=week)
        sub.save()


def transfer_hcp():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT week, year, golfer, handicap from main_handicapreal")

    # loop through each score object
    for row in cursor:

        # get data from score object
        week = int(row[0])
        year = int(row[1])
        golfer = int(row[2])
        handicap = float(row[3])

        print(week)
        print(year)
        print(golfer)
        print(handicap)

        season = Season.objects.get(year=year)
        week = Week.objects.get(number=week, season=season, rained_out=False)

        # get golfer name from ID
        for row in conn_old.execute(f'SELECT name from main_golfer WHERE id = {golfer}'):
            print(row)
            golfer_name = row[0]

        golfer = Golfer.objects.get(name=golfer_name)

        handicap = Handicap(handicap=handicap, week=week, golfer=golfer)

        handicap.save()

def transfer_holes():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT hole, par, handicap, handicap9, yards, year from main_hole")

    # loop through each score object
    for row in cursor:
        # get data from score object
        hole = int(row[0])
        par = int(row[1])
        handicap = int(row[2])
        handicap9 = int(row[3])
        yards = int(row[4])
        year = int(row[5])

        if year == 2019:
            season = Season.objects.get(year=2019)
            Hole(number=hole, par=par, handicap=handicap, handicap9=handicap9, yards=yards, season=season).save()
        if year == 2020:
            season = Season.objects.get(year=2020)
            Hole(number=hole, par=par, handicap=handicap, handicap9=handicap9, yards=yards, season=season).save()
            season = Season.objects.get(year=2021)
            Hole(number=hole, par=par, handicap=handicap, handicap9=handicap9, yards=yards, season=season).save()
            season = Season.objects.get(year=2022)
            Hole(number=hole, par=par, handicap=handicap, handicap9=handicap9, yards=yards, season=season).save()

def transfer_games():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT name, desc, week, year from main_game")

    # loop through each score object
    for row in cursor:
        # get data from score object
        name = int(row[0])
        desc = int(row[1])
        week = int(row[2])
        year = int(row[3])


def transfer_skinentries():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT golfer, week, year from main_skinentry")

    # loop through each score object
    for row in cursor:
        # get data from score object
        golfer = int(row[0])
        week = int(row[1])
        year = int(row[2])

        # get golfer name from ID
        for row in conn_old.execute(f'SELECT name from main_golfer WHERE id = {golfer}'):
            print(row)
            golfer_name = row[0]

        golfer_obj = Golfer.objects.get(name=golfer_name)
        week_obj = Week.objects.get(season=Season.objects.get(year=year), number=week, rained_out=False)

        SkinEntry(golfer=golfer_obj, week=week_obj).save()

def transfer_scores():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT golfer, week, score, hole, year from main_score")

    # loop through each score object
    for row in cursor:
        # get data from score object
        golfer = int(row[0])
        week = int(row[1])
        score = int(row[2])
        hole = int(row[3])
        year = int(row[4])

        # get golfer name from ID
        for row in conn_old.execute(f'SELECT name from main_golfer WHERE id = {golfer}'):
            print(row)
            golfer_name = row[0]

        golfer_obj = Golfer.objects.get(name=golfer_name)
        season_obj = Season.objects.get(year=year)
        week_obj = Week.objects.get(season=season_obj, number=week, rained_out=False)
        hole_obj = Hole.objects.get(season=season_obj, number=hole)

        Score(golfer=golfer_obj, week=week_obj, hole=hole_obj, score=score).save()


def transfer_games():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT name, desc, week, year from main_game")

    # loop through each score object
    for row in cursor:
        # get data from score object
        name = row[0]
        desc = row[1]
        week = int(row[2])
        year = int(row[3])

        season_obj = Season.objects.get(year=year)
        week_obj = Week.objects.get(season=season_obj, number=week, rained_out=False)

        Game(name=name, desc=desc, week=week_obj).save()

def transfer_gameentries():

    conn_old = sqlite3.connect('./data.sqlite3')

    # get all the scores from the old DB
    cursor = conn_old.execute("SELECT golfer, week, won, year from main_gameentry")

    # loop through each score object
    for row in cursor:
        # get data from score object
        golfer = int(row[0])
        week = int(row[1])
        won = bool(row[2])
        year = int(row[3])

        # get golfer name from ID
        for row in conn_old.execute(f'SELECT name from main_golfer WHERE id = {golfer}'):
            print(row)
            golfer_name = row[0]

        golfer_obj = Golfer.objects.get(name=golfer_name)
        season_obj = Season.objects.get(year=year)
        week_obj = Week.objects.get(season=season_obj, number=week, rained_out=False)
        game_obj = Game.objects.get(week=week_obj)

        GameEntry(golfer=golfer_obj, winner=won, game=game_obj, week=week_obj).save()