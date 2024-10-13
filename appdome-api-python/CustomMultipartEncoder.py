import os
from uuid import uuid4


class CustomMultipartEncoder:
    def __init__(self, fields, boundary=None, encoding='utf-8'):
        self.boundary_value = boundary or uuid4().hex
        self.boundary = f'--{self.boundary_value}'
        self.encoding = encoding
        self.fields = fields
        self._buffer = b''

    def _encode_field(self, name, value, filename=None, content_type=None):
        part = []
        part.append(f'{self.boundary}\r\n')
        if filename:
            part.append(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n')
        else:
            part.append(f'Content-Disposition: form-data; name="{name}"\r\n')

        if content_type:
            part.append(f'Content-Type: {content_type}\r\n')

        part.append('\r\n')
        if isinstance(value, bytes):
            part.append(value.decode(self.encoding))
        else:
            part.append(str(value))
        part.append('\r\n')

        return ''.join(part).encode(self.encoding)

    def _encode_file_field(self, name, file_path, content_type):
        with open(file_path, 'rb') as f:
            file_content = f.read()
        filename = os.path.basename(file_path)
        return self._encode_field(name, file_content, filename, content_type)

    def to_string(self):
        encoded = []

        # Iterate through fields and encode them
        for name, value in self.fields.items():
            if isinstance(value, tuple):
                filename, file_content, content_type = value
                encoded.append(self._encode_field(name, file_content, filename, content_type))
            else:
                encoded.append(self._encode_field(name, value))

        # Closing boundary
        encoded.append(f'{self.boundary}--\r\n'.encode(self.encoding))

        return b''.join(encoded)

    @property
    def content_type(self):
        return f'multipart/form-data; boundary={self.boundary_value}'