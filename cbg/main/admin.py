from django.contrib import admin
from django import forms

from .models import Golfer, Season, Team, Week, Game, GameEntry, SkinEntry, Hole, Score, Handicap, Matchup, Sub, Points, Round, GolferMatchup, RandomDrawnTeam


class GolferAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_teams_count', 'get_seasons_played')
    search_fields = ('name',)
    list_per_page = 50
    
    def get_teams_count(self, obj):
        return obj.team_set.count()
    get_teams_count.short_description = 'Teams'
    get_teams_count.admin_order_field = 'team__count'
    
    def get_seasons_played(self, obj):
        seasons = set()
        for team in obj.team_set.all():
            seasons.add(team.season.year)
        return ', '.join(map(str, sorted(seasons)))
    get_seasons_played.short_description = 'Seasons Played'


class SeasonAdmin(admin.ModelAdmin):
    list_display = ('year', 'get_teams_count', 'get_weeks_count', 'get_golfers_count')
    search_fields = ('year',)
    list_per_page = 20
    
    def get_teams_count(self, obj):
        return obj.team_set.count()
    get_teams_count.short_description = 'Teams'
    
    def get_weeks_count(self, obj):
        return obj.week_set.count()
    get_weeks_count.short_description = 'Weeks'
    
    def get_golfers_count(self, obj):
        return Golfer.objects.filter(team__season=obj).distinct().count()
    get_golfers_count.short_description = 'Golfers'


class TeamAdmin(admin.ModelAdmin):
    list_display = ('get_golfer1', 'get_golfer2', 'get_season', 'get_weeks_played')
    list_filter = ('season',)
    search_fields = ('golfers__name', 'season__year')
    list_per_page = 50
    
    fieldsets = (
        ('Team Information', {
            'fields': ('season', 'golfers')
        }),
    )
    
    def get_season(self, obj):
        return obj.season.year
    get_season.short_description = 'Season'
    get_season.admin_order_field = 'season__year'
    
    def get_golfer1(self, obj):
        golfers = obj.golfers.all()
        return golfers[0].name if golfers.count() > 0 else 'No golfer'
    get_golfer1.short_description = 'Golfer 1'
    
    def get_golfer2(self, obj):
        golfers = obj.golfers.all()
        return golfers[1].name if golfers.count() > 1 else 'No golfer'
    get_golfer2.short_description = 'Golfer 2'
    
    def get_weeks_played(self, obj):
        return obj.season.week_set.count()
    get_weeks_played.short_description = 'Weeks in Season'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('season').prefetch_related('golfers')


class WeekAdmin(admin.ModelAdmin):
    list_display = ('get_date', 'number', 'season', 'rained_out', 'is_front', 'get_scores_count', 'get_matchups_count')
    list_filter = ('season', 'rained_out', 'is_front')
    search_fields = ('date', 'season__year')
    list_per_page = 50
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Week Information', {
            'fields': ('season', 'date', 'number', 'rained_out', 'is_front')
        }),
        ('Scores', {
            'fields': ('num_scores',),
            'classes': ('collapse',)
        }),
    )
    
    def get_date(self, obj):
        return f"{obj.date.strftime('%Y-%m-%d')}"
    get_date.short_description = 'Date'
    get_date.admin_order_field = 'date'
    
    def get_scores_count(self, obj):
        return obj.score_set.count()
    get_scores_count.short_description = 'Scores'
    
    def get_matchups_count(self, obj):
        return obj.matchup_set.count()
    get_matchups_count.short_description = 'Matchups'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('season')


class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_week', 'get_entries_count')
    list_filter = ('week__season', 'week')
    search_fields = ('name', 'desc', 'week__date')
    list_per_page = 50
    
    fieldsets = (
        ('Game Information', {
            'fields': ('name', 'desc')
        }),
        ('Week Assignment', {
            'fields': ('week',),
            'classes': ('collapse',)
        }),
    )
    
    def get_week(self, obj):
        if obj.week:
            return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
        return "(No week assigned)"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_entries_count(self, obj):
        return obj.gameentry_set.count()
    get_entries_count.short_description = 'Entries'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('week')


class GameEntryAdmin(admin.ModelAdmin):
    list_display = ('game', 'get_golfer', 'get_week', 'winner')
    list_filter = ('game__week__season', 'game__week', 'winner', 'game')
    search_fields = ('game__name', 'golfer__name', 'week__date')
    list_per_page = 50
    
    fieldsets = (
        ('Entry Information', {
            'fields': ('game', 'golfer', 'week', 'winner')
        }),
    )
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    get_golfer.admin_order_field = 'golfer__name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('game', 'golfer', 'week')


class SkinEntryAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'winner')
    list_filter = ('week__season', 'week', 'winner')
    search_fields = ('golfer__name', 'week__date')
    list_per_page = 50
    
    fieldsets = (
        ('Skin Entry', {
            'fields': ('golfer', 'week', 'winner')
        }),
    )
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    get_golfer.admin_order_field = 'golfer__name'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('golfer', 'week')


class HoleAdmin(admin.ModelAdmin):
    list_display = ('number', 'par', 'yards', 'handicap', 'handicap9', 'get_season')
    list_filter = ('season', 'par')
    search_fields = ('number', 'season__year')
    list_per_page = 50
    
    fieldsets = (
        ('Hole Information', {
            'fields': ('number', 'par', 'yards', 'handicap', 'handicap9', 'season')
        }),
    )
    
    def get_season(self, obj):
        return obj.season.year
    get_season.short_description = 'Season'
    get_season.admin_order_field = 'season__year'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('season')


class ScoreAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'get_hole', 'score', 'get_par_diff')
    list_filter = ('week__season', 'week', 'hole', 'golfer')
    search_fields = ('golfer__name', 'week__date', 'hole__number')
    list_per_page = 100
    date_hierarchy = 'week__date'
    
    fieldsets = (
        ('Score Information', {
            'fields': ('golfer', 'week', 'hole', 'score')
        }),
    )
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    get_golfer.admin_order_field = 'golfer__name'
    
    def get_hole(self, obj):
        return f"Hole {obj.hole.number}"
    get_hole.short_description = 'Hole'
    get_hole.admin_order_field = 'hole__number'
    
    def get_par_diff(self, obj):
        diff = obj.score - obj.hole.par
        if diff > 0:
            return f"+{diff}"
        return str(diff)
    get_par_diff.short_description = 'vs Par'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('golfer', 'week', 'hole')


class HandicapAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'handicap', 'get_season')
    list_filter = ('week__season', 'week', 'golfer')
    search_fields = ('golfer__name', 'week__date')
    list_per_page = 100
    date_hierarchy = 'week__date'
    
    fieldsets = (
        ('Handicap Information', {
            'fields': ('golfer', 'week', 'handicap')
        }),
    )
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    get_golfer.admin_order_field = 'golfer__name'
    
    def get_season(self, obj):
        return obj.week.season.year
    get_season.short_description = 'Season'
    get_season.admin_order_field = 'week__season__year'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('golfer', 'week__season')


class MatchupAdmin(admin.ModelAdmin):
    list_display = ('get_week', 'team1', 'team2', 'get_season')
    list_filter = ('week__season', 'week')
    search_fields = ('week__date', 'teams__golfers__name')
    list_per_page = 50
    
    fieldsets = (
        ('Matchup Information', {
            'fields': ('week', 'teams')
        }),
    )
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'

    def team1(self, obj):
        teams = obj.teams.all()
        if teams.count() >= 1:
            golfers = teams[0].golfers.all()
            if golfers.count() >= 2:
                return f"{golfers[0].name} & {golfers[1].name}"
        return "Incomplete Team"
    team1.short_description = 'Team 1'

    def team2(self, obj):
        teams = obj.teams.all()
        if teams.count() >= 2:
            golfers = teams[1].golfers.all()
            if golfers.count() >= 2:
                return f"{golfers[0].name} & {golfers[1].name}"
        return "Incomplete Team"
    team2.short_description = 'Team 2'
    
    def get_season(self, obj):
        return obj.week.season.year
    get_season.short_description = 'Season'
    get_season.admin_order_field = 'week__season__year'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('week__season').prefetch_related('teams__golfers')


class SubAdminForm(forms.ModelForm):
    class Meta:
        model = Sub
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add empty choice to sub_golfer field
        self.fields['sub_golfer'].empty_label = "---------"
        
        # Make sub_golfer not required initially
        self.fields['sub_golfer'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        no_sub = cleaned_data.get('no_sub')
        sub_golfer = cleaned_data.get('sub_golfer')
        
        # If no_sub is True, ensure sub_golfer is None
        if no_sub:
            cleaned_data['sub_golfer'] = None
        # If no_sub is False, sub_golfer is required
        elif not sub_golfer:
            raise forms.ValidationError("Sub Golfer is required when 'No Sub' is not checked.")
        
        return cleaned_data


class SubAdmin(admin.ModelAdmin):
    form = SubAdminForm
    list_display = ('get_week', 'get_absent', 'get_sub', 'no_sub', 'get_season')
    list_filter = ('week__season', 'week', 'no_sub')
    search_fields = ('absent_golfer__name', 'sub_golfer__name', 'week__date')
    list_per_page = 50
    
    fieldsets = (
        ('Substitution Information', {
            'fields': ('week', 'absent_golfer', 'no_sub', 'sub_golfer')
        }),
    )
    
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.no_sub:
            form.base_fields['sub_golfer'].widget.attrs['readonly'] = True
            form.base_fields['sub_golfer'].widget.attrs['style'] = 'background-color: #f0f0f0;'
        return form
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_absent(self, obj):
        return obj.absent_golfer.name
    get_absent.short_description = 'Absent Golfer'
    get_absent.admin_order_field = 'absent_golfer__name'
    
    def get_sub(self, obj):
        if obj.sub_golfer:
            return obj.sub_golfer.name
        else:
            return 'No Sub'
    get_sub.short_description = 'Sub Golfer'
    get_sub.admin_order_field = 'sub_golfer__name'
    
    def get_season(self, obj):
        return obj.week.season.year
    get_season.short_description = 'Season'
    get_season.admin_order_field = 'week__season__year'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('absent_golfer', 'sub_golfer', 'week__season')
    
    def save_model(self, request, obj, form, change):
        # If no_sub is True, clear the sub_golfer field
        if obj.no_sub:
            obj.sub_golfer = None
        super().save_model(request, obj, form, change)


class PointsAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'get_hole', 'points', 'get_season')
    list_filter = ('week__season', 'week', 'hole', 'golfer')
    search_fields = ('golfer__name', 'week__date', 'hole__number')
    list_per_page = 100
    date_hierarchy = 'week__date'
    
    fieldsets = (
        ('Points Information', {
            'fields': ('golfer', 'week', 'hole', 'score', 'points')
        }),
    )
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    get_golfer.admin_order_field = 'golfer__name'
    
    def get_hole(self, obj):
        return f"Hole {obj.hole.number}"
    get_hole.short_description = 'Hole'
    get_hole.admin_order_field = 'hole__number'
    
    def get_season(self, obj):
        return obj.week.season.year
    get_season.short_description = 'Season'
    get_season.admin_order_field = 'week__season__year'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('golfer', 'week__season', 'hole', 'score')
    
    # Fix the verbose name
    def get_model_perms(self, request):
        perms = super().get_model_perms(request)
        perms['verbose_name'] = 'Points'
        perms['verbose_name_plural'] = 'Points'
        return perms


class RoundAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'get_matchup', 'gross', 'net', 'round_points', 'total_points', 'is_sub', 'get_subbing_for')
    list_filter = ('week__season', 'week', 'is_sub', 'golfer')
    search_fields = ('golfer__name', 'week__date', 'subbing_for__name')
    readonly_fields = ('gross', 'net', 'round_points', 'total_points')
    list_per_page = 50
    date_hierarchy = 'week__date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('golfer', 'week', 'matchup', 'golfer_matchup', 'handicap')
        }),
        ('Substitution Information', {
            'fields': ('is_sub', 'subbing_for'),
            'classes': ('collapse',)
        }),
        ('Scores and Points', {
            'fields': ('gross', 'net', 'round_points', 'total_points'),
            'classes': ('collapse',)
        }),
        ('Related Data', {
            'fields': ('points', 'scores'),
            'classes': ('collapse',)
        }),
    )
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    get_golfer.admin_order_field = 'golfer__name'
    
    def get_matchup(self, obj):
        try:
            teams = obj.matchup.teams.all()
            if teams.count() >= 2:
                team1 = teams[0]
                team2 = teams[1]
                golfers1 = team1.golfers.all()
                golfers2 = team2.golfers.all()
                if golfers1.count() >= 2 and golfers2.count() >= 2:
                    return f"{golfers1[0].name} & {golfers1[1].name} vs {golfers2[0].name} & {golfers2[1].name}"
        except:
            pass
        return f"Matchup {obj.matchup.id}"
    get_matchup.short_description = 'Matchup'
    
    def get_subbing_for(self, obj):
        if obj.subbing_for:
            return obj.subbing_for.name
        return "N/A"
    get_subbing_for.short_description = 'Subbing For'
    get_subbing_for.admin_order_field = 'subbing_for__name'
    
    def get_queryset(self, request):
        """Optimize queryset to reduce database queries"""
        return super().get_queryset(request).select_related(
            'golfer', 'week', 'matchup', 'golfer_matchup', 'handicap', 'subbing_for'
        ).prefetch_related(
            'matchup__teams__golfers', 'points', 'scores'
        )


class GolferMatchupAdmin(admin.ModelAdmin):
    list_display = ('get_golfer', 'get_week', 'get_opponent', 'is_A', 'is_teammate_subbing', 'get_subbing_for')
    list_filter = ('week__season', 'week', 'is_A', 'is_teammate_subbing', 'golfer')
    search_fields = ('golfer__name', 'opponent__name', 'week__date', 'subbing_for_golfer__name')
    list_per_page = 50
    date_hierarchy = 'week__date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('golfer', 'opponent', 'week', 'is_A')
        }),
        ('Substitution Information', {
            'fields': ('is_teammate_subbing', 'subbing_for_golfer'),
            'classes': ('collapse',)
        }),
    )
    
    def get_week(self, obj):
        return f"{obj.week.date.strftime('%Y-%m-%d')} (Week {obj.week.number})"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_golfer(self, obj):
        return obj.golfer.name
    get_golfer.short_description = 'Golfer'
    get_golfer.admin_order_field = 'golfer__name'
    
    def get_opponent(self, obj):
        return obj.opponent.name
    get_opponent.short_description = 'Opponent'
    get_opponent.admin_order_field = 'opponent__name'
    
    def get_subbing_for(self, obj):
        if obj.subbing_for_golfer:
            return obj.subbing_for_golfer.name
        return "N/A"
    get_subbing_for.short_description = 'Subbing For'
    get_subbing_for.admin_order_field = 'subbing_for_golfer__name'
    
    def get_queryset(self, request):
        """Optimize queryset to reduce database queries"""
        return super().get_queryset(request).select_related(
            'golfer', 'opponent', 'week', 'subbing_for_golfer'
        )


class RandomDrawnTeamAdmin(admin.ModelAdmin):
    list_display = ('get_week', 'get_absent_team', 'get_drawn_team', 'get_season')
    list_filter = ('week__season', 'week')
    search_fields = ('absent_team__golfers__name', 'drawn_team__golfers__name', 'week__date')
    list_per_page = 50
    
    fieldsets = (
        ('Random Drawn Team Information', {
            'fields': ('week', 'absent_team', 'drawn_team')
        }),
    )
    
    def get_week(self, obj):
        return f"Week {obj.week.number} - {obj.week.date.strftime('%Y-%m-%d')}"
    get_week.short_description = 'Week'
    get_week.admin_order_field = 'week__date'
    
    def get_absent_team(self, obj):
        return str(obj.absent_team)
    get_absent_team.short_description = 'Absent Team'
    
    def get_drawn_team(self, obj):
        return str(obj.drawn_team)
    get_drawn_team.short_description = 'Drawn Team'
    
    def get_season(self, obj):
        return obj.week.season.year
    get_season.short_description = 'Season'
    get_season.admin_order_field = 'week__season__year'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('week__season', 'absent_team', 'drawn_team').prefetch_related('absent_team__golfers', 'drawn_team__golfers')


# Register all models with their admin classes
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
admin.site.register(GolferMatchup, GolferMatchupAdmin)
admin.site.register(RandomDrawnTeam, RandomDrawnTeamAdmin)
