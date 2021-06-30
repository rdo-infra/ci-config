import dlrnapi_client


def main():
    label = 'previous-current-tripleo'
#    dlrnapi_client.configuration.username = 'ciuser'
#    dlrnapi_client.configuration.password = 'dlrnapi_password00'
    api_client = dlrnapi_client.ApiClient(
        host='https://trunk.rdoproject.org/api-centos8-master-uc')
    api_instance = dlrnapi_client.DefaultApi(api_client=api_client)
    hashesh_params = dlrnapi_client.PromotionQuery()
    hashesh_params.promote_name = label
    hashesh_params.limit = 1
    hashesh = api_instance.api_promotions_get(hashesh_params)
    print(hashesh[0])


if __name__ == '__main__':
    main()
