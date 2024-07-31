class Device():
    """
    Parent class device for device_list
    """

    def open(self, *args, **kwargs):
        return True

    def close(self, *args, **kwargs):
        return True
