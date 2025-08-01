(function($) {
    'use strict';
    
    $(document).ready(function() {
        // Get the week field and team fields
        var $weekField = $('#id_week');
        var $absentTeamField = $('#id_absent_team');
        var $drawnTeamField = $('#id_drawn_team');
        
        // Function to update team options
        function updateTeamOptions(weekId) {
            if (!weekId) {
                return;
            }
            
            // Get the current values to preserve selection if possible
            var currentAbsentTeam = $absentTeamField.val();
            var currentDrawnTeam = $drawnTeamField.val();
            
            // Show loading indicator
            $absentTeamField.prop('disabled', true);
            $drawnTeamField.prop('disabled', true);
            
            // Make AJAX request to get filtered teams
            $.ajax({
                url: '../filter-teams-by-week/',
                data: { 'week_id': weekId },
                dataType: 'json',
                success: function(data) {
                    // Clear existing options except the empty option
                    $absentTeamField.find('option:not(:first)').remove();
                    $drawnTeamField.find('option:not(:first)').remove();
                    
                    // Add new options
                    $.each(data.teams, function(index, team) {
                        var option = new Option(team.name, team.id);
                        $absentTeamField.append(option.cloneNode(true));
                        $drawnTeamField.append(option);
                    });
                    
                    // Restore previous selections if they still exist
                    if (currentAbsentTeam) {
                        $absentTeamField.val(currentAbsentTeam);
                    }
                    if (currentDrawnTeam) {
                        $drawnTeamField.val(currentDrawnTeam);
                    }
                    
                    // Re-enable fields
                    $absentTeamField.prop('disabled', false);
                    $drawnTeamField.prop('disabled', false);
                },
                error: function() {
                    // Re-enable fields even on error
                    $absentTeamField.prop('disabled', false);
                    $drawnTeamField.prop('disabled', false);
                    console.error('Failed to load teams for selected week');
                }
            });
        }
        
        // Update teams when week changes
        $weekField.on('change', function() {
            var weekId = $(this).val();
            if (weekId) {
                updateTeamOptions(weekId);
            } else {
                // Reset team fields if no week is selected
                $absentTeamField.find('option:not(:first)').remove();
                $drawnTeamField.find('option:not(:first)').remove();
            }
        });
        
        // If editing an existing object and week is already selected, load the teams
        if ($weekField.val()) {
            updateTeamOptions($weekField.val());
        }
    });
})(django.jQuery);