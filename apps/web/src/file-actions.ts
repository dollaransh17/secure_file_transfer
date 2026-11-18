import {QueryClient} from '@tanstack/react-query';
import {api} from './api';

type FileRecord = {id: string; name: string; [key: string]: unknown};
type FileDetails = {file: FileRecord; [key: string]: unknown};

export async function renameFile(client: QueryClient, id: string, name: string) {
  const result = await api<{ok: boolean}>('/files/' + id, {method: 'PATCH', body: JSON.stringify({name})});
  if (result.ok !== true) throw new Error('The server did not confirm the rename');

  const detailKey = ['detail-' + id];
  const filesKey = ['files'];
  // Discard reads begun before the committed rename. Update only metadata after
  // server confirmation; security evidence and version state remain untouched.
  await Promise.all([client.cancelQueries({queryKey: detailKey}), client.cancelQueries({queryKey: filesKey})]);
  client.setQueryData<FileDetails>(detailKey, current => current ? {...current, file: {...current.file, name}} : current);
  client.setQueryData<FileRecord[]>(filesKey, current => current?.map(file => file.id === id ? {...file, name} : file));
  await Promise.all([client.invalidateQueries({queryKey: detailKey}), client.invalidateQueries({queryKey: filesKey})]);
}
