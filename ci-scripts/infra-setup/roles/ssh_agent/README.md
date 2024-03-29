#ssh_agent

Role to start a `ssh_agent` and add a private key to it. This role store all
`ssh-agent` environment variables in `ssh_agent_environment` dict as ansible
fact, which can be further consumed to read ssh-agent keys.

## Variables
* `ssh_private_key_content`: (String) Raw content of a private key to be added to the ssh-agent. Default: ''

Example:
```yaml
- hosts: all
  tasks:
    - name: Start a ssh-agent and add a private key to it
      import_role:
        name: ssh_agent
      vars:
        ssh_private_key_content: |
          -----BEGIN RSA PRIVATE KEY-----
          MIIEowIBAAKCAQEAvJ5+qg0sA9rHFouk+tQeBq+FDDqHwzLTd1oyMFl+47Fp89jg
          6njfyBmJEyIeGA/AA1njMHDfHC1IWTN/9cgnxcN//gwtRVIsnDRMG8ylwqJNuKKa
          av7Xnxcu6N8PEYRjzRP8nMsCXVev+zi6Y8RdNsH9AOl/S4x+ms2aEs7b7ePI9pgK
          jvrxlKqyO0KVNXXk61s4SBMG+bcEjTNnzzCy5PiV9hlMuw5YERuVV5dMB6rskN5N
          o1O4bc102og1YzIwPAsqp0Hul2o9sKWl9CHcjIhLdx0U9hI2xVqF46+jG/hLlAX6
          kZ8rryxA4jSlxeIP9rDGR5lvwk7H9a7C0mdzLQIDAQABAoIBAQC34/YtqEXfRC6R
          ZnfkK2VSs1CNiYrO3gCY/hCsXrR9HHzlxe4R6uKR3YNsafjZEJHtMndyxLhgai18
          +d6pKwjLoDxq3EhOqzze1YXWHIEG7uHDPpQ5+FcTvbB4TPAN7fq29+NyoeGeS11B
          Gh9uIQWX2yzk9MCsUT8lgYnTCGYW2C3DpuUgajDjhq63NMEYpDnDMCu+SZpTzhfg
          gwpapf7Y93q4X5yDtFrxqaOPHB9h0cSTeJos7Vf25rDud5q/wcJW2azI+WgpgVDP
          uTgeEOjOKN1xH0ebBnmHYSVSfj9iQZdanRxsjcjBtiVzwGaE2gkJuWBeaRhradWU
          9gDujipBAoGBAOoREZOhDmWMqVRuz+536D8ewER2qE+zNt4+KLZatkrVOD14D1AW
          FCWg382sFgJyXB1EKdkp/94B++FBmcwY9YpI4zCRzbNxLXQXtJCIguujCGetlLzl
          wJyj1AiQnvuAJWqtWFAWv126eAvje6AS/Et44IrxOTw/RjMIQ/pLAEV5AoGBAM5L
          M/kLLNko/2kCd6qa8ltZq9MbJD6na19cX0cewDIzUioYmQEUGhZV9rNei/2+8LE6
          lxZ20DUlfdap8PqKhn16+RnIHf7k1934lHuh7kLNr9OoFRH2YSVGJK9L83RxIhVQ
          qPlZEsu0x0gt35jZeq26Chx8tqMWLBWmQL8BxPJVAoGAVD+iiPWufeS8ShS8qQPl
          x1plL/9Zo55JAIN1GfXaqWLHpHBjapsX01dtVtU68tSAzVPskCrq2tjx9WksV2cg
          cg68H45LcOwqxR+HMYLBRNlgvBihccBsrLTXK+IKJ1I/pX8RS3p0lOL6NKVDqSFM
          SEoQ4FHlHQdVWCcAeMWoKlkCgYBn3B7PfJvYvTZRxQdAYoAwE6ZZQ2ntDVcWjKf/
          Y3D6FTKBtR6bF2bG5gKtbaVnXBFL+SaGDc1nZHfFcou7Z7CsThRJsaHAabBwtazz
          zaPqCCpEknQBNhzUqkrf4oowjqDNQG3CE+FNo7dNFKNlDeEgw/BBRVyiIRCS2b/x
          Kk/gfQKBgA+GWI6bjA0zGdjBsElaX0tt3vtJN1rZW/fYSA3FZ2KvdPTxmP/N0pzZ
          PXOzGohcXPGPYFALq1XO8NqDnzVD6sokwkD/n1UKiDOmrB+iRuBXzAleECLarIzi
          WAsyy1Jag5MFgLJysZEKUDPtFWvsrs3gdn63GcrqkOH85a2Y/X2U
          -----END RSA PRIVATE KEY-----
```
