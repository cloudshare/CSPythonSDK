import argparse

from csapi.cslowapi import ApiException, CSLowApi, prettify_json

def main():
    parser = argparse.ArgumentParser(description="CloudShare API command line utility")
    parser.add_argument("-i","--id", help="CloudShare API ID", required=True, metavar='API-ID',dest='api_id')
    parser.add_argument("-k","--key", help="CloudShare API Key", required=True, metavar='API-KEY', dest='api_key')
    parser.add_argument("-m","--category", help="The API command category", required=True, metavar='CATEGORY', dest='category')
    parser.add_argument("-c","--command", help="The API command", required=True, metavar='COMMAND', dest='command')
    parser.add_argument("-p","--params", help="Command's parameters. List of key-value pairs", metavar='KEY VALUE', dest='params', nargs="*")
    parser.add_argument("-f","--fire", help="Execute API call", action='store_const', dest='fire', default=False, const=True)

    args = parser.parse_args()
    
    if args.params == None:
        params = {}
    elif len(args.params) % 2 != 0:
        parser.error("Parameters should be key-value pairs. e.g. -p KEY0 VALUE0 KEY1 VALUE1")
    else:
        params = dict(zip(args.params[0::2], args.params[1::2]))

    api = CSLowApi(args.api_id, args.api_key)

    print("\n\nURL: {0}".format(api.gen_url(args.category, args.command, params)))

    if args.fire:
        try:
            res = api.call(args.category, args.command, **params)
        except ApiException as e:
            res = e

        print('--------------------------- RESPONSE ------------------')
        print(prettify_json(res.content))
        print('--------------------------- END      ------------------')
        print('Status code: {0}'.format(res.code))
        
if __name__ == '__main__':
    main()