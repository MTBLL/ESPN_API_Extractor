from espn_api_extractor.utils.logger import Logger


class CoreRunner:
    def __init__(self, argumentParser, runner_name: str, output_dir: str):
        self.args = argumentParser.parse_args()
        # Override args with function parameters if provided
        if output_dir is not None:
            setattr(self.args, "output_dir", output_dir)

        self.year = self.args.year  # type: ignore
        assert self.year is not None
        self.threads = self.args.threads  # type: ignore
        self.batch_size = self.args.batch_size  # type: ignore
        self.force_full_extraction = self.args.force_full_extraction  # type: ignore
        self.graphql_config_path = self.args.graphql_config  # type: ignore

        self.logger = Logger(runner_name)
