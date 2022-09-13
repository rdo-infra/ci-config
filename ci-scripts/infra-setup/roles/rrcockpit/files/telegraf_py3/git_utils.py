import os
import git


def fire_testproj(output, ref):

    testproj_base_path = os.getenv('testproj_base_path')
    repo = git.Repo(testproj_base_path)
    os.chdir(testproj_base_path)
    origin = repo.remotes.origin
    origin.pull(ref)
    zuul_file = open(os.path.join(testproj_base_path, ".zuul.yaml"),
                     "w")
    zuul_file.write(output)
    zuul_file.close()
    repo.git.add([zuul_file])
    # NOW HOW TO COMMIT AND PUSH?