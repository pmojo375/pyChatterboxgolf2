from django.contrib import admin

from .models import Golfer, Season, Team, Week, Game, GameEntry, SkinEntry, Hole, Score, Handicap, Matchup, Sub, Points, Round


class GolferAdmin(admin.ModelAdmin):
    list_display = ('name',)


class SeasonAdmin(admin.ModelAdmin):
    list_display = ('year',)


class TeamAdmin(admin.ModelAdmin):
    list_display = ('get_golfer1', 'get_golfer2', 'get_season')
    
    def get_season(self, obj):
        return obj.season.year
    get_season.short_description = 'Season'
    
    def get_golfer1(self, obj):
        return obj.golfers.all()[0].name
    get_golfer1.short_description = 'Golfer 1'
    
    def get_golfer2(self, obj):
        return obj.golfers.all()[1].name
    get_golfer2.short_description = 'Golfer 2'


class WeekAdmin(admin.ModelAdmin):
    list_display = ('get_date', 'number', 'season', 'rained_out', 'is_front')
    
    def get_date(self, obj):
        return f"{obj.date.strftime('%Y-%m-%d')}"


class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'desc', 'get_week')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'


class GameEntryAdmin(admin.ModelAdmin):
    list_display = ('game', 'get_golfer', 'get_week', 'winner')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'


class SkinEntryAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'winner')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'


class HoleAdmin(admin.ModelAdmin):
    list_display = ('number', 'par', 'yards', 'get_season')
    
    def get_season(self, obj):
        return obj.season.year
    get_season.short_description = 'Season'


class ScoreAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'get_hole', 'score')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    
    def get_hole(self, obj):
        return f"Hole {obj.hole.number}"
    get_hole.short_description = 'Hole'


class HandicapAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'handicap')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'


class MatchupAdmin(admin.ModelAdmin):
    list_display = ('get_week', 'team1', 'team2')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'

    def team1(self, obj):
        return f"{obj.teams.all()[0].golfers.all()[0].name} & {obj.teams.all()[0].golfers.all()[1].name}"
    team1.short_description = 'Team 1'

    def team2(self, obj):
        return f"{obj.teams.all()[1].golfers.all()[0].name} & {obj.teams.all()[1].golfers.all()[1].name}"
    team2.short_description = 'Team 2'



class SubAdmin(admin.ModelAdmin):
    list_display = ('get_week', 'get_absent', 'get_sub')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    
    def get_absent(self, obj):
        return obj.absent_golfer.name
    get_absent.short_description = 'Absent Golfer'
    
    def get_sub(self, obj):
        return obj.sub_golfer.name
    get_sub.short_description = 'Absent Golfer'


class PointsAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'hole', 'score', 'points')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'


class RoundAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'matchup', 'gross', 'net', 'round_points')
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'


admin.site.register(Golfer, GolferAdmin)
admin.site.register(Season, SeasonAdmin)
admin.site.register(Team, TeamAdmin)
admin.site.register(Week, WeekAdmin)
admin.site.register(Game, GameAdmin)
admin.site.register(GameEntry, GameEntryAdmin)
admin.site.register(SkinEntry, SkinEntryAdmin)
admin.site.register(Hole, HoleAdmin)
admin.site.register(Score, ScoreAdmin)
admin.site.register(Handicap, HandicapAdmin)
admin.site.register(Matchup, MatchupAdmin)
admin.site.register(Sub, SubAdmin)
admin.site.register(Points, PointsAdmin)
admin.site.register(Round, RoundAdmin)
