from django.test import TestCase
from django.db.models import Sum
from datetime import timedelta
from django.utils import timezone
from main.models import *
from main.helper import get_current_season, get_last_week, get_next_week, get_week, get_golfer_points, calculate_and_save_handicaps_for_season, generate_golfer_matchups, generate_rounds
import random
from django.urls import reverse


class GenerateGolferMatchupsTests(TestCase):
    def setUp(self):
        self.season = Season.objects.create(year=timezone.now().year)
        self.week = Week.objects.create(date=timezone.now(), season=self.season, number=1, rained_out=False, is_front=True)
        self.golfer1 = Golfer.objects.create(name='Team 1 Golfer 1')
        self.golfer2 = Golfer.objects.create(name='Team 1 Golfer 2')
        self.golfer3 = Golfer.objects.create(name='Team 2 Golfer 1')
        self.golfer4 = Golfer.objects.create(name='Team 2 Golfer 2')
        self.sub1 = Golfer.objects.create(name='Test Sub 1')
        self.sub2 = Golfer.objects.create(name='Test Sub 2')
        self.sub3 = Golfer.objects.create(name='Test Sub 3')
        self.sub4 = Golfer.objects.create(name='Test Sub 4')

        for i in range(1, 19):
            Hole.objects.create(number=i, par=random.uniform(3, 5), handicap=i, handicap9=(i if i<=9 else i-9), yards=250, season=self.season) 

        self.team1 = Team.objects.create(season=self.season)
        self.team1.save()
        self.team1.golfers.add(self.golfer1, self.golfer2)
        self.team1.save()
        
        self.team2 = Team.objects.create(season=self.season)
        self.team2.save()
        self.team2.golfers.add(self.golfer3, self.golfer4)
        self.team2.save()

        self.matchup = Matchup(week=self.week)
        self.matchup.save()
        self.matchup.teams.add(self.team1, self.team2)
        self.matchup.save()

    def test_generate_golfer_matchups(self):
        # Test with no subs
        generate_golfer_matchups(self.week)
        self.assertEqual(GolferMatchup.objects.count(), 4)
        self.assertEqual(GolferMatchup.objects.filter(is_A=True).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(is_A=False).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer1).count(), 1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer2).count(), 1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer3).count(), 1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer4).count(), 1)

        # remove all golfer matchups
        GolferMatchup.objects.all().delete()

    def test_golfer_matchups_with_sub(self):
        Sub.objects.create(week=self.week, absent_golfer=self.golfer1, sub_golfer=self.sub1)

        generate_golfer_matchups(self.week)

        self.assertEqual(GolferMatchup.objects.count(), 4)
        self.assertEqual(GolferMatchup.objects.filter(is_A=True).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(is_A=False).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer1).count(), 0)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.sub1).count(), 1)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.sub1).subbing_for_golfer, self.golfer1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer2).count(), 1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer3).count(), 1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer4).count(), 1)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer2).subbing_for_golfer, None)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer3).subbing_for_golfer, None)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer4).subbing_for_golfer, None)

        # remove all golfer matchups
        GolferMatchup.objects.all().delete()


    def test_golfer_matchups_with_multiple_subs_one_team(self):
        Sub.objects.create(week=self.week, absent_golfer=self.golfer1, sub_golfer=self.sub1)
        Sub.objects.create(week=self.week, absent_golfer=self.golfer2, sub_golfer=self.sub2)

        generate_golfer_matchups(self.week)

        self.assertEqual(GolferMatchup.objects.count(), 4)
        self.assertEqual(GolferMatchup.objects.filter(is_A=True).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(is_A=False).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer1).count(), 0)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.sub1).count(), 1)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.sub1).subbing_for_golfer, self.golfer1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer2).count(), 0)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.sub2).count(), 1)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.sub2).subbing_for_golfer, self.golfer2)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer3).count(), 1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer4).count(), 1)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer3).subbing_for_golfer, None)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer4).subbing_for_golfer, None)

        # remove all golfer matchups
        GolferMatchup.objects.all().delete()

    def test_golfer_matchups_with_a_no_sub(self):
        Sub.objects.create(week=self.week, absent_golfer=self.golfer1, no_sub=True)

        generate_golfer_matchups(self.week)

        self.assertEqual(GolferMatchup.objects.count(), 4)
        self.assertEqual(GolferMatchup.objects.filter(is_A=True).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(is_A=False).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer1).count(), 0)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer2, subbing_for_golfer=self.golfer1).exists(), True)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer2).count(), 2)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer3).count(), 1)
        self.assertEqual(GolferMatchup.objects.filter(golfer=self.golfer4).count(), 1)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer2, subbing_for_golfer=None).subbing_for_golfer, None)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer3, subbing_for_golfer=None).subbing_for_golfer, None)
        self.assertEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer4, subbing_for_golfer=None).subbing_for_golfer, None)
        self.assertNotEqual(GolferMatchup.objects.get(week=self.week, golfer=self.golfer2, subbing_for_golfer=self.golfer1).subbing_for_golfer, None)

        # remove all golfer matchups
        GolferMatchup.objects.all().delete()

class SeasonWeekTests(TestCase):

    def setUp(self):
        # Setting up data for the tests
        self.current_year = timezone.now().year
        self.past_date = timezone.now() - timedelta(weeks=1)
        self.future_date = timezone.now() + timedelta(weeks=1)
        
        # Create a current season
        self.current_season = Season.objects.create(year=self.current_year)
        
        # Create weeks for the current season
        self.past_week = Week.objects.create(season=self.current_season, date=self.past_date, number=1, rained_out=False, is_front=True)
        self.future_week = Week.objects.create(season=self.current_season, date=self.future_date, number=3, rained_out=False, is_front=False)

        self.hole = Hole.objects.create(number=1, par=4, handicap=2, handicap9=1, yards=478, season=self.current_season)

        self.score = Score.objects.create(golfer=Golfer.objects.create(name='Test Golfer'), week=self.past_week, score=75, hole=self.hole)

    def test_get_current_season_exists(self):
        # Test when the current season exists
        season = get_current_season()
        self.assertIsNotNone(season)
        self.assertEqual(season.year, self.current_year)

    def test_get_current_season_not_exists(self):
        # Test when the current season does not exist
        Season.objects.all().delete()  # Remove the current season
        season = get_current_season()
        self.assertIsNone(season)

    def test_get_last_week_exists(self):
        # Test when the current season exists and there is a past week
        week = get_last_week()
        self.assertIsNotNone(week)
        self.assertEqual(week.date.day, self.past_date.day)
        self.assertEqual(week.date.month, self.past_date.month)
        self.assertEqual(week.date.year, self.past_date.year)

    def test_get_last_week_no_past_weeks(self):
        # Test when the current season exists but there are no past weeks
        pass

    def test_get_last_week_no_season(self):
        # Test when the current season does not exist
        Season.objects.all().delete()  # Remove the current season
        week = get_last_week()
        self.assertIsNone(week)

    def test_get_next_week_exists(self):
        # Test when the current season exists and there is a future week
        week = get_next_week()
        self.assertIsNotNone(week)
        future_date = timezone.now() + timedelta(weeks=1)
        self.assertEqual(week.date.day, future_date.day)
        self.assertEqual(week.date.month, future_date.month)
        self.assertEqual(week.date.year, future_date.year)

    def test_get_next_week_no_future_weeks(self):
        # Test when the current season exists but there are no future weeks
        pass

    def test_get_next_week_no_season(self):
        # Test when the current season does not exist
        Season.objects.all().delete()  # Remove the current season
        week = get_next_week()
        self.assertIsNone(week)

class RoundTestCase(TestCase):
    def setUp(self):
        self.current_date = timezone.now().date()
        self.season = Season.objects.create(year=self.current_date.year)
        self.week1 = Week.objects.create(date=self.current_date - timedelta(days=7), season=self.season, number=1, rained_out=False, is_front=True)
        
        self.team1_golfer1 = Golfer.objects.create(name='Team 1 Test Golfer 1') # Hcp 12 playing golfer 2 hcp 9 - 3 strokes gotten
        self.team1_golfer2 = Golfer.objects.create(name='Team 1 Test Golfer 2') # Hcp 14 playing golfer 1 hcp 11 - 3 strokes gotten
        self.team2_golfer1 = Golfer.objects.create(name='Team 2 Test Golfer 1') # Hcp 11 playing golfer 2 hcp 14 - 3 strokes given
        self.team2_golfer2 = Golfer.objects.create(name='Team 2 Test Golfer 2') # Hcp 9 playing golfer 1 hcp 12 - 3 strokes given
        
        self.team1_golfer1_hcp = Handicap.objects.create(golfer=self.team1_golfer1, week=self.week1, handicap=12)
        self.team1_golfer2_hcp = Handicap.objects.create(golfer=self.team1_golfer2, week=self.week1, handicap=14)
        self.team2_golfer1_hcp = Handicap.objects.create(golfer=self.team2_golfer1, week=self.week1, handicap=11)
        self.team2_golfer2_hcp = Handicap.objects.create(golfer=self.team2_golfer2, week=self.week1, handicap=9)
        
        
        self.team1 = Team.objects.create(season=self.season)
        self.team1.golfers.add(self.team1_golfer1, self.team1_golfer2)
        self.team1.save()
        
        self.team2 = Team.objects.create(season=self.season)
        self.team2.golfers.add(self.team2_golfer1, self.team2_golfer2)
        self.team2.save()
        
        self.matchup = Matchup(week=self.week1)
        self.matchup.save()
        
        self.matchup.teams.add(self.team1, self.team2)
        self.matchup.save()
        
        # Create scores for the golfer2 on team 1 and 2
        self.team1_golfer1_scores = [4, 6, 4, 8, 9, 5, 6, 6, 8] #56 12 3.5pts 44 0pts 3.5pts
                                   # 3  5  3 
                                   # 1  0  1  0  0 .5  0  1  0  
        self.team2_golfer2_scores = [7, 3, 6, 6, 6, 5, 4, 7, 6] #50 9 5.5pts 41 3pts 8.5pts

        self.team1_golfer2_scores = [5, 4, 5, 7, 7, 4, 7, 8, 4] #51 14 6pts 37 3pts 9pts
                                   # 4  3  4 
                                   # 1  1  1  1 .5 .5  0  0  1  
        self.team2_golfer1_scores = [6, 8, 9, 8, 7, 4, 6, 5, 5] #58 11 3pts 47 0pts 3pts
        
        for i in range(1, 19):
            Hole.objects.create(number=i, par=random.uniform(3, 5), handicap=i, handicap9=(i if i<=9 else i-9), yards=250, season=self.season) 

        for i, score in enumerate(self.team1_golfer1_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team1_golfer1, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team1_golfer2_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team1_golfer2, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team2_golfer1_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team2_golfer1, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team2_golfer2_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team2_golfer2, week=self.week1, score=score, hole=self.hole)

        generate_golfer_matchups(self.week1)

    def test_round_generate(self):
        
        generate_rounds(self.season)
        
        round = Round.objects.get(golfer=self.team1_golfer1, week=self.week1)
        
        self.assertEqual(round.gross, 56)
        self.assertEqual(round.net, 44)
        self.assertEqual(round.points.aggregate(Sum('points'))['points__sum'], 3.5)
        self.assertEqual(round.total_points, 3.5)
        self.assertEqual(round.matchup, self.matchup)
        self.assertEqual(round.week, self.week1)
        self.assertEqual(round.round_points, 0)
        
class HandicapTestCase(TestCase):
    def setUp(self):
        
        # Set the current date
        self.current_date = timezone.now().date()
        
        # Create test season
        self.season = Season.objects.create(year=self.current_date.year)
        
        # Create test weeks
        self.week8 = Week.objects.create(date=self.current_date, season=self.season, number=8, rained_out=False, is_front=False)
        self.week7 = Week.objects.create(date=self.current_date - timedelta(days=7), season=self.season, number=7, rained_out=False, is_front=True)
        self.week6 = Week.objects.create(date=self.current_date - timedelta(days=14), season=self.season, number=6, rained_out=False, is_front=False)
        self.week5 = Week.objects.create(date=self.current_date - timedelta(days=21), season=self.season, number=5, rained_out=False, is_front=True)
        self.week4 = Week.objects.create(date=self.current_date - timedelta(days=28), season=self.season, number=4, rained_out=False, is_front=False)
        self.week3 = Week.objects.create(date=self.current_date - timedelta(days=35), season=self.season, number=3, rained_out=False, is_front=True)
        self.week2 = Week.objects.create(date=self.current_date - timedelta(days=42), season=self.season, number=2, rained_out=False, is_front=False)
        self.week1 = Week.objects.create(date=self.current_date - timedelta(days=49), season=self.season, number=1, rained_out=False, is_front=True)
        
        # Create test golfers
        self.golfer1 = Golfer.objects.create(name='Test Golfer 1') # Played all 7 weeks - 13.28 - Weeks 1, 2, 3 and 4 should be the same
        self.golfer2 = Golfer.objects.create(name='Test Golfer 2') # Less than 3 weeks - 14 - All weeks should be the same
        self.golfer3 = Golfer.objects.create(name='Test Golfer 3') # Missed a week in first 3 weeks but played all 7 - 13.6 - Weeks 1, 3, 4 and 5 should be the same
        self.golfer4 = Golfer.objects.create(name='Test Golfer 4') # More than 3 weeks but less than 5 - 14.2 - Weeks 1, 2, 3 and 4 should be the same
        self.golfer5 = Golfer.objects.create(name='Test Golfer 5') # Missed week 4 - 13.8 - Weeks 1, 2, 3 and 5 should be the same
        
        for i in range(1, 19):
            Hole.objects.create(number=i, par=random.uniform(3, 5), handicap=i, handicap9=(i if i<= 9 else i-9), yards=250, season=self.season) 

        # Create scores for the golfers
        self.week1scores = [4, 6, 4, 8, 9, 5, 6, 6, 8] #56
        self.week2scores = [5, 4, 5, 7, 7, 4, 7, 8, 4] #51
        self.week3scores = [6, 8, 9, 8, 7, 4, 6, 5, 5] #58
        self.week4scores = [7, 3, 6, 6, 6, 5, 4, 7, 6] #50
        self.week5scores = [4, 4, 4, 6, 5, 3, 6, 7, 5] #44
        self.week6scores = [5, 9, 6, 4, 7, 3, 8, 7, 4] #53
        self.week7scores = [8, 5, 7, 6, 4, 4, 5, 8, 6] #53

        # Create scores for the golfers
        for i, score in enumerate(self.week1scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.golfer1, week=self.week1, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer2, week=self.week1, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer3, week=self.week1, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer4, week=self.week1, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer5, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.week2scores):
            self.hole = Hole.objects.get(number=i + 10)
            Score.objects.create(golfer=self.golfer1, week=self.week2, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer2, week=self.week2, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer4, week=self.week2, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer5, week=self.week2, score=score, hole=self.hole)
        for i, score in enumerate(self.week3scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.golfer1, week=self.week3, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer3, week=self.week3, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer4, week=self.week3, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer5, week=self.week3, score=score, hole=self.hole)
        for i, score in enumerate(self.week4scores):
            self.hole = Hole.objects.get(number=i + 10)
            Score.objects.create(golfer=self.golfer1, week=self.week4, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer3, week=self.week4, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer4, week=self.week4, score=score, hole=self.hole)
        for i, score in enumerate(self.week5scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.golfer1, week=self.week5, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer3, week=self.week5, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer5, week=self.week5, score=score, hole=self.hole)
        for i, score in enumerate(self.week6scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.golfer1, week=self.week6, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer3, week=self.week6, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer5, week=self.week6, score=score, hole=self.hole)
        for i, score in enumerate(self.week7scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.golfer1, week=self.week7, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer3, week=self.week7, score=score, hole=self.hole)
            Score.objects.create(golfer=self.golfer5, week=self.week7, score=score, hole=self.hole)

    def test_create_handicap(self):
        calculate_and_save_handicaps_for_season(self.season)

        golfer1_hcp_week8 = Handicap.objects.get(golfer=self.golfer1, week=self.week8).handicap
        golfer1_hcp_week1 = Handicap.objects.get(golfer=self.golfer1, week=self.week1).handicap
        golfer1_hcp_week2 = Handicap.objects.get(golfer=self.golfer1, week=self.week2).handicap
        golfer1_hcp_week3 = Handicap.objects.get(golfer=self.golfer1, week=self.week3).handicap
        golfer1_hcp_week4 = Handicap.objects.get(golfer=self.golfer1, week=self.week4).handicap
        
        golfer2_hcp_week3 = Handicap.objects.get(golfer=self.golfer2, week=self.week3).handicap
        golfer2_hcp_week2 = Handicap.objects.get(golfer=self.golfer2, week=self.week2).handicap
        golfer2_hcp_week1 = Handicap.objects.get(golfer=self.golfer2, week=self.week1).handicap
        
        golfer3_hcp_week8 = Handicap.objects.get(golfer=self.golfer3, week=self.week8).handicap
        golfer3_hcp_week1 = Handicap.objects.get(golfer=self.golfer3, week=self.week1).handicap
        golfer3_hcp_week3 = Handicap.objects.get(golfer=self.golfer3, week=self.week3).handicap
        golfer3_hcp_week4 = Handicap.objects.get(golfer=self.golfer3, week=self.week4).handicap
        golfer3_hcp_week5 = Handicap.objects.get(golfer=self.golfer3, week=self.week5).handicap
        
        golfer4_hcp_week1 = Handicap.objects.get(golfer=self.golfer4, week=self.week1).handicap
        golfer4_hcp_week2 = Handicap.objects.get(golfer=self.golfer4, week=self.week2).handicap
        golfer4_hcp_week3 = Handicap.objects.get(golfer=self.golfer4, week=self.week3).handicap
        golfer4_hcp_week4 = Handicap.objects.get(golfer=self.golfer4, week=self.week4).handicap
        golfer4_hcp_week5 = Handicap.objects.get(golfer=self.golfer4, week=self.week5).handicap
        
        golfer5_hcp_week8 = Handicap.objects.get(golfer=self.golfer5, week=self.week8).handicap
        golfer5_hcp_week1 = Handicap.objects.get(golfer=self.golfer5, week=self.week1).handicap
        golfer5_hcp_week2 = Handicap.objects.get(golfer=self.golfer5, week=self.week2).handicap
        golfer5_hcp_week3 = Handicap.objects.get(golfer=self.golfer5, week=self.week3).handicap
        golfer5_hcp_week5 = Handicap.objects.get(golfer=self.golfer5, week=self.week5).handicap
        
        # Assert that the handicap was created and has the correct value
        self.assertEqual(golfer1_hcp_week8, 13.28)
        self.assertEqual(golfer2_hcp_week3, 14)
        self.assertEqual(golfer3_hcp_week8, 13.6)
        self.assertEqual(golfer4_hcp_week5, 14.2)
        self.assertEqual(golfer5_hcp_week8, 13.8)

        self.assertEqual(golfer1_hcp_week4, golfer1_hcp_week1)
        self.assertEqual(golfer1_hcp_week4, golfer1_hcp_week2)
        self.assertEqual(golfer1_hcp_week4, golfer1_hcp_week3)
        
        self.assertEqual(golfer2_hcp_week3, golfer2_hcp_week2)
        self.assertEqual(golfer2_hcp_week3, golfer2_hcp_week1)
        
        self.assertEqual(golfer3_hcp_week5, golfer3_hcp_week1)
        self.assertEqual(golfer3_hcp_week5, golfer3_hcp_week3)
        self.assertEqual(golfer3_hcp_week5, golfer3_hcp_week4)

        self.assertEqual(golfer4_hcp_week4, golfer4_hcp_week1)
        self.assertEqual(golfer4_hcp_week4, golfer4_hcp_week2)
        self.assertEqual(golfer4_hcp_week4, golfer4_hcp_week3)
        
        self.assertEqual(golfer5_hcp_week5, golfer5_hcp_week1)
        self.assertEqual(golfer5_hcp_week5, golfer5_hcp_week2)
        self.assertEqual(golfer5_hcp_week5, golfer5_hcp_week3)

class PointsTestCase(TestCase):
    def setUp(self):
        '''
        Need to create other test cases:
        1) Subs - DONE
        2) Single subs
        3) Single golfer non-sub
        3) Handicap Ties
        '''
        
        self.current_date = timezone.now().date()
        
        self.season = Season.objects.create(year=self.current_date.year)
        
        self.week1 = Week.objects.create(date=self.current_date, season=self.season, number=1, rained_out=False, is_front=True)
        
        # Normal Matchup
        self.team1_golfer1 = Golfer.objects.create(name='Team 1 Test Golfer 1') # Hcp 12 playing golfer 2 hcp 9 - 3 strokes gotten
        self.team1_golfer2 = Golfer.objects.create(name='Team 1 Test Golfer 2') # Hcp 14 playing golfer 1 hcp 11 - 3 strokes gotten
        self.team2_golfer1 = Golfer.objects.create(name='Team 2 Test Golfer 1') # Hcp 11 playing golfer 2 hcp 14 - 3 strokes given
        self.team2_golfer2 = Golfer.objects.create(name='Team 2 Test Golfer 2') # Hcp 9 playing golfer 1 hcp 12 - 3 strokes given
        
        # Sub Matchup
        self.team3_golfer1 = Golfer.objects.create(name='Team 3 Test Golfer 1') # Hcp 12 playing golfer 1 hcp 11 - 1 stroke gotten
        self.team3_golfer2 = Golfer.objects.create(name='Team 3 Test Golfer 2') # Absent
        self.team3_golfer2_sub = Golfer.objects.create(name='Team 3 Test Golfer 2 Sub') # Hcp 10 playing golfer 2 hcp 9 - 1 stroke gotten
        self.team4_golfer1 = Golfer.objects.create(name='Team 4 Test Golfer 1') # Hcp 11 playing golfer 1 hcp 12 - 1 stroke given
        self.team4_golfer2 = Golfer.objects.create(name='Team 4 Test Golfer 2') # Hcp 9 playing golfer 2 Sub hcp 10 - 1 stroke given
        
        self.team1_golfer1_hcp = Handicap.objects.create(golfer=self.team1_golfer1, week=self.week1, handicap=12)
        self.team1_golfer2_hcp = Handicap.objects.create(golfer=self.team1_golfer2, week=self.week1, handicap=14)
        self.team2_golfer1_hcp = Handicap.objects.create(golfer=self.team2_golfer1, week=self.week1, handicap=11)
        self.team2_golfer2_hcp = Handicap.objects.create(golfer=self.team2_golfer2, week=self.week1, handicap=9)
        
        self.team3_golfer1_hcp = Handicap.objects.create(golfer=self.team3_golfer1, week=self.week1, handicap=12)
        self.team3_golfer2_hcp = Handicap.objects.create(golfer=self.team3_golfer2, week=self.week1, handicap=14)
        self.team3_golfer2_sub_hcp = Handicap.objects.create(golfer=self.team3_golfer2_sub, week=self.week1, handicap=10)
        self.team4_golfer1_hcp = Handicap.objects.create(golfer=self.team4_golfer1, week=self.week1, handicap=11)
        self.team4_golfer2_hcp = Handicap.objects.create(golfer=self.team4_golfer2, week=self.week1, handicap=9)
        
        self.team1 = Team.objects.create(season=self.season)
        self.team1.golfers.add(self.team1_golfer1, self.team1_golfer2)
        self.team1.save()
        
        self.team2 = Team.objects.create(season=self.season)
        self.team2.golfers.add(self.team2_golfer1, self.team2_golfer2)
        self.team2.save()
        
        self.matchup = Matchup(week=self.week1)
        self.matchup.save()
        
        self.matchup.teams.add(self.team1, self.team2)
        self.matchup.save()
        
        self.team3 = Team.objects.create(season=self.season)
        self.team3.golfers.add(self.team3_golfer1, self.team3_golfer2)
        self.team3.save()
        
        self.team4 = Team.objects.create(season=self.season)
        self.team4.golfers.add(self.team4_golfer1, self.team4_golfer2)
        self.team4.save()
        
        #Create matchup for team3 and 4
        self.matchup2 = Matchup(week=self.week1)
        self.matchup2.save()
        
        self.matchup2.teams.add(self.team3, self.team4)
        self.matchup2.save()
        
        
        self.sub = Sub(week=self.week1, absent_golfer=self.team3_golfer2, sub_golfer=self.team3_golfer2_sub)
        self.sub.save()
        

        for i in range(1, 19):
            Hole.objects.create(number=i, par=random.uniform(3, 5), handicap=i, handicap9=(i if i<=9 else i-9), yards=250, season=self.season) 

        # Create scores for the golfer2 on team 1 and 2
        self.team1_golfer1_scores = [4, 6, 4, 8, 9, 5, 6, 6, 8] #56 12 3.5pts 44 0pts 3.5pts
                                   # 3  5  3 
                                   # 1  0  1  0  0 .5  0  1  0  
        self.team2_golfer2_scores = [7, 3, 6, 6, 6, 5, 4, 7, 6] #50 9 5.5pts 41 3pts 8.5pts

        self.team1_golfer2_scores = [5, 4, 5, 7, 7, 4, 7, 8, 4] #51 14 6pts 37 3pts 9pts
                                   # 4  3  4 
                                   # 1  1  1  1 .5 .5  0  0  1  
        self.team2_golfer1_scores = [6, 8, 9, 8, 7, 4, 6, 5, 5] #58 11 3pts 47 0pts 3pts
        
        # Create scores for the golfers on team 3 and 4
        self.team3_golfer1_scores = [4, 6, 4, 8, 9, 5, 6, 6, 8] #56 12 4pts 44 3pts 7pts
                                   # 3   
                                   # 1  1  1 .5  0  0 .5  0  0  
        self.team4_golfer1_scores = [6, 8, 9, 8, 7, 4, 6, 5, 5] #58 11 5pts 47 0pts 5pts

        self.team3_golfer2_sub_scores = [5, 4, 5, 7, 7, 4, 7, 8, 4] #51 10 4pts 41 1.5pts 5.5pts
                                       # 4 
                                       # 1  0  1  0  0  1  0  0  1  
        self.team4_golfer2_scores =     [7, 3, 6, 6, 6, 5, 4, 7, 6] #50 9  5pts 41 1.5pts 6.5pts
        
        

        for i, score in enumerate(self.team1_golfer1_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team1_golfer1, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team1_golfer2_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team1_golfer2, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team2_golfer1_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team2_golfer1, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team2_golfer2_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team2_golfer2, week=self.week1, score=score, hole=self.hole)

        for i, score in enumerate(self.team3_golfer1_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team3_golfer1, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team3_golfer2_sub_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team3_golfer2_sub, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team4_golfer1_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team4_golfer1, week=self.week1, score=score, hole=self.hole)
        for i, score in enumerate(self.team4_golfer2_scores):
            self.hole = Hole.objects.get(number=i + 1)
            Score.objects.create(golfer=self.team4_golfer2, week=self.week1, score=score, hole=self.hole)
 
        generate_golfer_matchups(self.week1)
        
    def test_get_points(self):
        self.team1_golfer1_pts = get_golfer_points(self.week1, self.team1_golfer1)
        self.team1_golfer2_pts = get_golfer_points(self.week1, self.team1_golfer2)
        self.team2_golfer1_pts = get_golfer_points(self.week1, self.team2_golfer1)
        self.team2_golfer2_pts = get_golfer_points(self.week1, self.team2_golfer2)
        
        self.team3_golfer1_pts = get_golfer_points(self.week1, self.team3_golfer1)
        self.team3_golfer2_sub_pts = get_golfer_points(self.week1, self.team3_golfer2_sub)
        self.team4_golfer1_pts = get_golfer_points(self.week1, self.team4_golfer1)
        self.team4_golfer2_pts = get_golfer_points(self.week1, self.team4_golfer2)

        # Assert that the points are correct
        self.assertEqual(self.team1_golfer1_pts, 3.5)
        self.assertEqual(self.team1_golfer2_pts, 9)
        self.assertEqual(self.team2_golfer1_pts, 3)
        self.assertEqual(self.team2_golfer2_pts, 8.5)
        
        self.assertEqual(self.team3_golfer1_pts, 7)
        self.assertEqual(self.team3_golfer2_sub_pts, 5.5)
        self.assertEqual(self.team4_golfer1_pts, 5)
        self.assertEqual(self.team4_golfer2_pts, 6.5)

        self.assertEqual(self.team1_golfer1_pts + self.team1_golfer2_pts + self.team2_golfer1_pts + self.team2_golfer2_pts, 24)
        self.assertEqual(self.team3_golfer1_pts + self.team3_golfer2_sub_pts + self.team4_golfer1_pts + self.team4_golfer2_pts, 24)

class AddRoundViewTests(TestCase):

    def setUp(self):
        self.current_date = timezone.now().date()
        self.season = Season.objects.create(year=self.current_date.year)
        self.golfer = Golfer.objects.create(name='John Doe')
        self.week = Week.objects.create(date=self.current_date, season=self.season, number=1, rained_out=False, is_front=True)
        for i in range(1, 19):
            Hole.objects.create(number=i, par=random.uniform(3, 5), handicap=i, handicap9=(i if i<= 9 else i-9), yards=250, season=self.season) 


    def test_add_round_view_uses_correct_template(self):
        response = self.client.get(reverse('add_round'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_round.html')

    def test_add_round_view_creates_new_round(self):
        post_data = {
            'golfer': self.golfer.id,
            'week': self.week.id,
            'hole1': 4,
            'hole2': 5,
            'hole3': 3,
            'hole4': 4,
            'hole5': 5,
            'hole6': 6,
            'hole7': 5,
            'hole8': 8,
            'hole9': 4
        }

        response = self.client.post(reverse('add_round'), data=post_data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Score.objects.filter(golfer=self.golfer, week=self.week).count(), 9)

class AddGolferViewTests(TestCase):

    def setUp(self):
        self.golfer = Golfer.objects.create(name='John Doe')

    def test_add_golfer_view_uses_correct_template(self):
        response = self.client.get(reverse('add_golfer'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_golfer.html')

    def test_add_golfer_view_creates_new_golfer(self):
        post_data = {
            'name': self.golfer.name
        }

        response = self.client.post(reverse('add_golfer'), data=post_data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Golfer.objects.get(id=self.golfer.id), self.golfer)

class AddSubViewTests(TestCase):

    def setUp(self):
        self.current_date = timezone.now().date()
        self.season = Season.objects.create(year=self.current_date.year)
        self.week = Week.objects.create(date=self.current_date, season=self.season, number=1, rained_out=False, is_front=True)
        self.absent_golfer = Golfer.objects.create(name='John Doe')
        self.team = Team.objects.create(season=self.season)
        self.team.golfers.add(self.absent_golfer)
        self.sub_golfer = Golfer.objects.create(name='Jim Doe')

    def test_add_sub_view_uses_correct_template(self):
        response = self.client.get(reverse('add_sub'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_sub.html')

    def test_add_sub_view_creates_new_golfer(self):
        post_data = {
            'absent_golfer': self.absent_golfer.id,
            'sub_golfer': self.sub_golfer.id,
            'week': self.week.id,
            'no_sub': False
        }

        response = self.client.post(reverse('add_sub'), data=post_data)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Sub.objects.filter(absent_golfer=self.absent_golfer, sub_golfer=self.sub_golfer, week=self.week).exists())

        if Sub.objects.filter(absent_golfer=self.absent_golfer, sub_golfer=self.sub_golfer, week=self.week).exists():
            sub = Sub.objects.get(absent_golfer=self.absent_golfer, sub_golfer=self.sub_golfer, week=self.week)
            self.assertEqual(sub.absent_golfer, self.absent_golfer)
            self.assertEqual(sub.sub_golfer, self.sub_golfer)
            self.assertEqual(sub.week, self.week)
        else:
            self.fail('Sub not created')