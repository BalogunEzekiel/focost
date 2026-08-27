from app.seeds.rbac_seed import RBACSeed


class SeedManager:

    @staticmethod
    def run(seed_name):

        seed_name = seed_name.lower()

        if seed_name == "rbac":
            RBACSeed.run()
            return

        if seed_name == "all":
            RBACSeed.run()
            return

        print(f"Unknown seed '{seed_name}'")