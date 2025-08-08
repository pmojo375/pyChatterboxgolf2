from rest_framework import serializers
from .models import Sub, GolferMatchup, Handicap
from main.helper import *

class GolferSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()  # Return either the golfer's name or the sub's name
    handicap = serializers.SerializerMethodField()  # Return the golfer's handicap
    gray_out = serializers.SerializerMethodField()  # Determine if the row should be grayed out
    golfer_id = serializers.IntegerField(source='id')  # Include the golfer's ID for score attribution
    is_A = serializers.BooleanField()  # Include the is_A field to determine pairing

    class Meta:
        model = GolferMatchup  # This should reference the GolferMatchup model
        fields = ['name', 'handicap', 'gray_out', 'golfer_id', 'is_A']  # Only return relevant fields

    def get_name(self, obj):
        subbing_for_golfer = obj.subbing_for_golfer

        if subbing_for_golfer is not None:
            sub = Sub.objects.filter(week=self.context['week'], absent_golfer=subbing_for_golfer).first()
            if sub and not sub.no_sub:
                return sub.sub_golfer.name
        return obj.golfer.name

    def get_handicap(self, obj):
        if Handicap.objects.filter(golfer=obj.golfer, week=self.context['week']).exists():
            return Handicap.objects.get(golfer=obj.golfer, week=self.context['week']).handicap
        else:
            return 'N/A'

    def get_gray_out(self, obj):

        subbing_for_golfer = obj.subbing_for_golfer

        if subbing_for_golfer is not None:
            sub = Sub.objects.filter(week=self.context['week'], absent_golfer=subbing_for_golfer).first()

            if sub and sub.no_sub:
                return True
        
        return False
