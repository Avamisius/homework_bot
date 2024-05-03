# import logging
# import sys

# from logging import StreamHandler


# logging.basicConfig(
#     level=logging.DEBUG,
#     # filename='program.log',
#     # filemode='w',
#     format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
#     handlers=[StreamHandler(sys.stdout)]
# )

# # logger = logging.getLogger(__name__)
# # logger.setLevel(logging.DEBUG)
# # formatter = logging.Formatter(
# #     u'%(asctime)s - %(name)s - %(levelname)s - %(message)s'
# # )
# # handler = StreamHandler(sys.stdout)
# # handler.setFormatter(formatter)
# # logger.addHandler(handler)


import logging
import sys

file_handler = logging.FileHandler(filename='tmp.log')
stdout_handler = logging.StreamHandler(stream=sys.stdout)
handlers = [file_handler, stdout_handler]

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
    handlers=handlers
)

logger = logging.getLogger('LOGGER_NAME')

logger.debug('123')
