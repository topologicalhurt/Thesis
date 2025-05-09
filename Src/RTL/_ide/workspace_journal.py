# 2025-05-08T14:31:32.751480
import vitis

client = vitis.create_client()
client.set_workspace(path='RTL')

client.sync_git_example_repo(name='vitis_hls_examples')
