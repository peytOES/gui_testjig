from birch.gui import JobSelectFrame


class JaguarJobSelectFrame(JobSelectFrame):
    def set_suite_list(self, l):
        """
        Set the list of test suites to offer for testing

        Every list item is a list of
        [name, cib remaining, cib total, description]
        """
        self.jobmgr = l
        self.lb.ClearAll()
        self.lb.InsertColumn(0, "Name", width=250)
        self.lb.InsertColumn(1, "Description", width=300)
        self.lb.InsertColumn(2, "Units Tested", width=150)
        index = 0
        for text in self.jobmgr.get_job_stats():
            for c in range(len(text)):
                if text[c] == None:
                    text[c] = ""

            line_text = [text[0], text[1], text[4]]
            self.lb.Append(line_text)
        self.lb.Select(0)
