class Version:
    def __init__(self, major, minor, hotfix):
        self.major = major
        self.minor = minor
        self.hotfix = hotfix

    def full_string(self):
        return "{0}.{1}.{2}".format(self.major, self.minor, self.hotfix)

    def short_string(self):
        return "{0}.{1}".format(self.major, self.minor)

    def get_next_minor_release(self):
        return Version(self.major, self.minor + 1, 0)

    def get_next_major_release(self):
        return Version(self.major + 1, 0, 0)

    def get_next_hotfix(self):
        return Version(self.major, self.minor, self.hotfix + 1)

    def get_last_hotfix(self):
        return Version(self.major, self.minor, self.hotfix - 1)

    def get_last_version_short(self):
        if self.minor == 0:
            return Version(self.major - 1, 0, 0).short_string()
        else:
            return Version(self.major, self.minor - 1, 0).short_string()

