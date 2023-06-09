class Candidate:
    def __init__(self, path):
        self.input_path = path
        self.output_path = path.replace(".csv", "_converted.csv").replace("uploads", "outputs")
        self.input_cols_string = None
        self.cols_mapping = None
        self.data_conversion_code = None
