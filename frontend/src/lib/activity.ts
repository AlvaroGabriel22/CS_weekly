export interface ActivityFormData {
  title: string
  description: string
}

export interface PendingFile {
  id: string
  file: File
  preview?: string
  isImage: boolean
}

export const emptyActivityForm = (): ActivityFormData => ({
  title: '',
  description: '',
})
