# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: model.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0bmodel.proto\"\x1e\n\x05Input\x12\x15\n\rinput_message\x18\x01 \x01(\t\"\'\n\rOutputMessage\x12\x16\n\x0eoutput_message\x18\x01 \x01(\t26\n\x07Predict\x12+\n\x11\x45nergyConsumption\x12\x06.Input\x1a\x0e.OutputMessageb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'model_pb2', _globals)
if _descriptor._USE_C_DESCRIPTORS == False:
  DESCRIPTOR._options = None
  _globals['_INPUT']._serialized_start=15
  _globals['_INPUT']._serialized_end=45
  _globals['_OUTPUTMESSAGE']._serialized_start=47
  _globals['_OUTPUTMESSAGE']._serialized_end=86
  _globals['_PREDICT']._serialized_start=88
  _globals['_PREDICT']._serialized_end=142
# @@protoc_insertion_point(module_scope)
