import '@testing-library/jest-dom/vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import FileAttachment, { type FileAttachmentData } from '../../predictions/FileAttachment';

const mockOnAttach = vi.fn();
const mockOnClear = vi.fn();

function renderAttachment(current: FileAttachmentData | null = null) {
  return render(
    <FileAttachment
      onAttach={mockOnAttach}
      onClear={mockOnClear}
      current={current}
    />
  );
}

function makeFile(name: string, type: string, sizeBytes = 1024) {
  const content = new Uint8Array(sizeBytes);
  return new File([content], name, { type });
}

describe('FileAttachment', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders paperclip button when no attachment', () => {
    renderAttachment();
    expect(screen.getByRole('button', { name: 'Attach file' })).toBeInTheDocument();
  });

  it('renders filename chip when attachment present', () => {
    renderAttachment({
      type: 'image',
      filename: 'test.jpg',
      content: 'abc',
      media_type: 'image/jpeg',
      context_text: '[Image: test.jpg]',
    });
    expect(screen.getByText('test.jpg')).toBeInTheDocument();
    expect(screen.getByLabelText('Remove attachment')).toBeInTheDocument();
  });

  it('calls onClear when remove button clicked', () => {
    renderAttachment({
      type: 'image',
      filename: 'test.jpg',
      content: 'abc',
      media_type: 'image/jpeg',
      context_text: '[Image: test.jpg]',
    });
    fireEvent.click(screen.getByLabelText('Remove attachment'));
    expect(mockOnClear).toHaveBeenCalledOnce();
  });

  it('shows error for unsupported file type', async () => {
    renderAttachment();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = makeFile('doc.pdf', 'application/pdf');
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/unsupported file type/i)).toBeInTheDocument();
    });
  });

  it('shows error for oversized file', async () => {
    renderAttachment();
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = makeFile('big.jpg', 'image/jpeg', 6 * 1024 * 1024);
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByText(/too large/i)).toBeInTheDocument();
    });
  });
});