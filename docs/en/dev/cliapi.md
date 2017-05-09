# CLI Api


'''
pirus version : return version
pirus help  : return help
pirus pipelines help : return pipeline help
pirus pipelines list [filters]: return list of pipeline avaible
pirus pieplines show <name> : return information of pipeline <name>
pirus pipelines rem <name> : uninstall a pipeline
pirus pieplines add <path> : install a new pipeline
pirus [runs] list [filters] : show list of runs
pirus [runs] stop <id> : stop a run
pirus [runs] pause <id> : pause a run
pirus [runs] start <pipeline> --input <path> --output <path> --config <config>
prius [runs] show <id> : show run information
pirus [runs] inputs <id> : show files input
pirus [runs] outputs <id> : show files output
pirus [runs] logs <id> : show run log
pirus [runs] cd <id> : Change directory to the current run
pirus config : set pirus configuration
'''