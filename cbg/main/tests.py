from django.test import TestCase
from datetime import date, timedelta
from django.utils import timezone
from main.models import *
from main.helper import get_week, calculate_handicap, get_golfer_points, calculate_and_save_handicaps_for_season
import random

class WeekTestCase(TestCase):
    def setUp(self):
        self.current_date = timezone.now().date()
        self.season = Season.objects.create(year=self.current_date.year)
        self.golfer = Golfer.objects.create(name='Test Golfer')
        self.hole = Hole.objects.create(number=1, par=4, handicap=2, handicap9=1, yards=478, season=self.season)
        self.week1 = Week.objects.create(date=self.current_date - timedelta(days=14), season=self.season, number=1, rained_out=False, is_front=True)
        self.week2 = Week.objects.create(date=self.current_date - timedelta(days=7), season=self.season, number=2, rained_out=False, is_front=False)
        Score.objects.create(golfer=self.golfer, week=self.week1, score=75, hole=self.hole)

    def test_get_week(self):
        # Test with no scores posted
        week = get_week(offset=False)
        self.assertEqual(week, self.week2)

        # Test with scores posted
        week = get_week(offset=True)
        self.assertEqual(week, self.week1)


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
        self.current_date = timezone.now().date()
        self.season = Season.objects.create(year=self.current_date.year)
        self.week1 = Week.objects.create(date=self.current_date - timedelta(days=35), season=self.season, number=1, rained_out=False, is_front=True)
        self.team1_golfer1 = Golfer.objects.create(name='Team 1 Test Golfer 1')
        self.team1_golfer2 = Golfer.objects.create(name='Team 1 Test Golfer 2')
        self.team2_golfer1 = Golfer.objects.create(name='Team 2 Test Golfer 1')
        self.team2_golfer2 = Golfer.objects.create(name='Team 2 Test Golfer 2')
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


        for i in range(1, 19):
            Hole.objects.create(number=i, par=random.uniform(3, 5), handicap=i, handicap9=(i if i<= 9 else i-9), yards=250, season=self.season) 

        # Create scores for the golfer
        self.team1_golfer1_scores = [4, 6, 4, 8, 9, 5, 6, 6, 8] #56 12.3 3.5pts 44 0pts 3.5pts
                                   # 3  5  3 
                                   # 1  0  1  0  0 .5  0  1  0  
        self.team2_golfer2_scores = [7, 3, 6, 6, 6, 5, 4, 7, 6] #50 9 5.5pts 41 3pts 8.5pts

        self.team1_golfer2_scores = [5, 4, 5, 7, 7, 4, 7, 8, 4] #51 14 6pts 37 3pts 9pts
                                   # 4  3  4 
                                   # 1  1  1  1 .5 .5  0  0  1  
        self.team2_golfer1_scores = [6, 8, 9, 8, 7, 4, 6, 5, 5] #58 11.4 3pts 47 0pts 3pts

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
 

    def test_get_points(self):
        self.team1_golfer1_pts = get_golfer_points(self.week1, self.team1_golfer1, detail=True)
        self.team1_golfer2_pts = get_golfer_points(self.week1, self.team1_golfer2, detail=True)
        self.team2_golfer1_pts = get_golfer_points(self.week1, self.team2_golfer1, detail=True)
        self.team2_golfer2_pts = get_golfer_points(self.week1, self.team2_golfer2, detail=True)

        # Assert that the points are correct
        self.assertEqual(self.team1_golfer1_pts['golfer_points'], 3.5)
        self.assertEqual(self.team1_golfer2_pts['golfer_points'], 9)
        self.assertEqual(self.team2_golfer1_pts['golfer_points'], 3)
        self.assertEqual(self.team2_golfer2_pts['golfer_points'], 8.5)

        self.assertEqual(self.team1_golfer1_pts['golfer_points'] + self.team1_golfer2_pts['golfer_points'] + self.team2_golfer1_pts['golfer_points'] + self.team2_golfer2_pts['golfer_points'], 24)

from django.urls import reverse

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

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Golfer.objects.get(id=self.golfer.id), self.golfer)

class AddSubViewTests(TestCase):

    def setUp(self):
        self.current_date = timezone.now().date()
        self.season = Season.objects.create(year=self.current_date.year)
        self.week = Week.objects.create(date=self.current_date, season=self.season, number=1, rained_out=False, is_front=True)
        self.absent_golfer = Golfer.objects.create(name='John Doe')
        self.sub_golfer = Golfer.objects.create(name='Jim Doe')

    def test_add_sub_view_uses_correct_template(self):
        response = self.client.get(reverse('add_sub'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_sub.html')

    def test_add_sub_view_creates_new_golfer(self):
        post_data = {
            'absent_golfer': self.absent_golfer.id,
            'sub_golfer': self.sub_golfer.id,
            'week': self.week.id
        }

        response = self.client.post(reverse('add_sub'), data=post_data)

        self.assertEqual(response.status_code, 302)
        sub = Sub.objects.get(absent_golfer=self.absent_golfer, sub_golfer=self.sub_golfer, week=self.week)
        self.assertEqual(sub.absent_golfer, self.absent_golfer)
        self.assertEqual(sub.sub_golfer, self.sub_golfer)
        self.assertEqual(sub.week, self.week)