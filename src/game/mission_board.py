class MissionBoard:
    def __init__(self):
        self.missions = []
        self.completed_missions = []

    def get_missions(self):
        return self.missions

    def add_mission(self, mission):
        self.missions.append(mission)

    def complete_mission(self, mission):
        if mission in self.missions:
            self.missions.remove(mission)
            self.completed_missions.append(mission)
            return True
        return False

    def get_completed_missions(self):
        return self.completed_missions