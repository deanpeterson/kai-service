#
# This script takes directoriy with yaml rulesets and checks if there rule without/with emtpy description field.
#
# Example usage: $ python hack/check_descriptions.py default/generated/technology-usage
#
import os
import sys
import yaml

# Use variable below for automatic rewrite of ruleset files
rewrite = False

rules_dir = sys.argv[1]
if not rules_dir or not os.path.isdir(rules_dir):
   print("ERROR: invalid rules directory. Provide it as a first argument to this script.")
   exit(2)

checked_cnt = 0
missing_cnt = 0
print(rules_dir)
rulesets = [os.path.join(rules_dir, f) for f in os.listdir(rules_dir) if os.path.isfile(
    os.path.join(rules_dir, f)) and f.endswith(".yaml") and not f.endswith("ruleset.yaml")]

for ruleset in rulesets:
   rules = dict()
   with open(ruleset) as data:
      try:
         print
         print("#######################################################################")
         print(ruleset)
         print("#######################################################################")
         print

         rules = yaml.safe_load(data)
         for rule in rules:
            checked_cnt += 1
            if rule.get("description") == None or rule["description"] == "":
               missing_cnt += 1
               print("  " + rule["ruleID"])
               # Guess based on when condition
               if rule.get("when"):
                 tags = rule.get("when").get("builtin.hasTags")   # Guess by Condition Tag
                 if tags and len(tags) == 1:
                    print("    description might be: %s" % tags[0])
                    if rewrite:
                       rule['description'] = tags[0]
                 else:
                   tag = rule.get("tag")  # Guess by (given) Tag
                   if tag and len(tag) == 1:
                     print("    description might be: %s" % tag[0])
                     if rewrite:
                       rule['description'] = tag[0]
      except yaml.YAMLError as exc:
        print(exc)
        exit(1)

   if rewrite:
      with open(ruleset, 'w') as rulesfile:
         yaml.dump(rules, rulesfile)

print
print("Checked %d rules and missing description for %d rules." % (checked_cnt, missing_cnt))
print(missing_cnt)
if missing_cnt < 1:
   exit(0)
else:
   exit(1)
