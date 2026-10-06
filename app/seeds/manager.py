from app.seeds.rbac_seed import RBACSeed
from app.seeds.compliance_seed import seed_policies


class SeedManager:

    @staticmethod
    def run(seed_name):

        seed_name = seed_name.lower()

        if seed_name == "rbac":
            RBACSeed.run()
            return

        if seed_name == "compliance":
            seed_policies()
            return

        if seed_name == "all":
            RBACSeed.run()
            seed_policies()
            return

        print(f"Unknown seed '{seed_name}'")