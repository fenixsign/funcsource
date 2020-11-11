"""
TODO:
1. Сделать декоратор для класса, который позволяет кэшировать некоторые внутренние методы,
используя кэш на диске.
"""

from contextlib import contextmanager
import os
import traceback
import json
import pickle

try:
    import requests
    from bs4 import BeautifulSoup as _BeautifulSoup
    import yaml
    import pandas as pd
except:
    imports = """
    import requests
    from bs4 import BeautifulSoup as _BeautifulSoup
    import yaml
    import pandas as pd
    """.split('\n')


    class tcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[31m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'


    for i in imports:
        try:
            exec(i.strip())
        except ModuleNotFoundError as e:
            print(tcolors.WARNING + repr(e) + tcolors.ENDC)


# Used as @fs.cached
def cached(cache, key=lambda *args, **kwargs: args):
    """Decorator to wrap a function with a memoizing callable that saves
    results in a cache.

    main idea from cachetools.cached

    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            k = key(*args, **kwargs)
            try:
                return cache[k]
            except KeyError:
                pass  # key not found
            v = func(*args, **kwargs)
            try:
                cache[k] = v
            except ValueError:
                pass  # value too large
            return v
        return wrapper
    return decorator


@contextmanager
def cache_args_pkl(call_func, dumppath=''):
    # default_cache = cachetools.TTLCache(ttl=777600)   # ttl = 10 days
    # default_cache = cachetools.TTLCache(100, ttl=777600)   # ttl = 10 days

    # because tuple saved in dict by id in memory, and can have two identical keys but with different ids
    # cache = {tuple(k): v for k, v in self.read_dump(name, {}).items()}

    if dumppath and not dumppath.endswith('/'):
        dumppath = dumppath + '/'

    dumppath = dumppath + '__pkl_cashe_dump__/'
    os.makedirs(dumppath, exist_ok=True)

    dumpfile = dumppath + call_func.__name__ + '.pkl'

    try:
        with open(dumpfile, 'rb') as f:
            cache = pickle.load(f)
    except:
        cache = {}

    f = cached(cache=cache)(call_func)

    try:
        yield f

    except BaseException as e:  # example: KeyboardInterrupt
        write_file(dumpfile, cache, 'pkl')
        raise e

    write_file(dumpfile, cache, 'pkl')


def decor_dump_to_pkl(display_name, dumppath):
    """
    cache first hard_work function result to pkl file and load it instead work of it
    """

    # if not ISLOCAL or not DumpFlag or not os.path.exists(ISLOCAL):
    #
    #     def no_decorate(call_func):
    #         return call_func
    #
    #     return no_decorate

    # dumppath = dumppath + '/' + display_name + '/__pkl_cashe_dump__/'
    dumppath = dumppath + '/__pkl_cashe_dump__/'
    os.makedirs(dumppath, exist_ok=True)

    def decorator(call_func):
        def wrapper(*args, **kwargs):
            filename = dumppath + call_func.__name__ + '.pkl'
            if os.path.exists(filename):
                result = read_file(filename)
                return result
            else:
                result = call_func(*args, **kwargs)
                write_file(filename, result, 'pkl')
                return result
        return wrapper

    return decorator


def url_get(url, proxies=False, headers=None):

    if not proxies:
        proxies = {}
    with requests.Session() as session:
        return session.get(url, headers=headers, proxies=proxies).content


def soup(content='', headers=None):

    if content.startswith('http'):
        content = url_get(content, headers=headers)

    if content:
        _soup = _BeautifulSoup(content, 'lxml')
        # soup.find('title', attrs={'itemprop': "name"})
        return _soup
    return None


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict()
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, BaseException):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def jdumps(o, indent=2, ensure_ascii=0, sort_keys=1, cls=CustomJSONEncoder, **kwargs):

    return json.dumps(o, ensure_ascii=ensure_ascii, indent=indent, sort_keys=sort_keys, cls=cls, **kwargs)


def ydumps(o):
    # TODO: need read about custom encoders
    return yaml.safe_dump(o, allow_unicode=True)


def read_file(filename, TYPE=True, errors='ignore', **kwargs):
    """
    read file with kwargs:
    Defult TYPE = extpath of file

    TYPE variants:
        pkl: pickle.load(f)
        yaml: yaml.load(f)
        json: json.load(f)
        None or another: f.read()

    additional args:
    mode = 'r' - mode kwarg of open func
        byte mode auto set encoding=None
    encoding = 'utf-8' - encoding kwarg of open func.

    """

    mode = kwargs.get('mode', 'r')
    encoding = kwargs.get('encoding', 'utf-8') if 'b' not in mode else None

    if TYPE and isinstance(TYPE, bool):
        TYPE = os.path.splitext(filename)[-1][1:]
    try:
        if TYPE == 'pkl':
            with open(filename, 'rb') as f:
                return pickle.load(f)

        with open(filename, mode=mode, encoding=encoding) as f:
            if TYPE == 'yaml':
                return yaml.safe_load(f)
            elif TYPE == "json":
                return json.loads(f.read())
            # elif TYPE == 'csv':
            #     return list(csv.reader(f, **kwargs))
            else:
                return f.read()

    except Exception as e:
        print(traceback.format_exc())
        if errors != 'ignore':
            raise e


def write_file(filename, input, mode=None):
    try:
        ext = filename.rsplit('.')[-1]
        if mode is None and ext in {'json', 'yml', 'pkl'}:
            raise ValueError(f'If you save file with .{ext} extesnion, you need to set mode')
            #
            # if ext in {'json', 'yml', 'pkl'}:
            #     print(f'WARNING!!! YOU SAVE {ext} IN RAW MODE')
            # with open(filename, 'w') as f:
            #     f.write(input)

        elif mode == 'wb' or isinstance(input, bytes):
            with open(filename, 'wb') as f:
                f.write(input)

        elif mode == 'pkl':
            if hasattr(input, 'to_pickle'):
                try:
                    return input.to_pickle(filename)
                except Exception:
                    pass

            with open(filename, 'wb') as f:
                pickle.dump(input, f)

        else:
            with open(filename, 'w') as f:
                if mode == 'json':
                    f.write(jdumps(input))
                elif mode == 'yaml':
                    f.write(ydumps(input))
                else:
                    f.write(input)
        return True
    except Exception as e:
        return repr(e)



@contextmanager
def catch_exceptions(*exceptions, message=None):
    """
    manager for catch exceptions
    Application examples:

    >>> with catch_exceptions():
    ...     1/0
    ZeroDivisionError('division by zero',)

    >>> with catch_exceptions(KeyError, ZeroDivisionError):
    ...     1/0
    ZeroDivisionError('division by zero',)

    >>> with catch_exceptions(KeyError):
    ...     1/0
    ...
    Traceback (most recent call last):
          ...
    ZeroDivisionError: division by zero
    """
    if not exceptions:
        exceptions = (Exception,)
    try:
        yield
    except exceptions as e:
        try:
            if message is None:
                message = 'MANAGER CATCH '

            if message:
                print(message + f'Exception: {repr(e)} \n traceback: {traceback.format_exc()}')
        except Exception as e:
            pass

    return True