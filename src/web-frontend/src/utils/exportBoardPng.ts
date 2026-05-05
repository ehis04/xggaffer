import {
  PITCH_VIEWBOX_HEIGHT,
  PITCH_VIEWBOX_WIDTH,
} from './pitchCoords';

interface ExportBoardPngOptions {
  fileName?: string;
  scale?: number;
}

const SVG_NAMESPACE = 'http://www.w3.org/2000/svg';
const SVG_XLINK_NAMESPACE = 'http://www.w3.org/1999/xlink';
const DEFAULT_SCALE = 2;
const DEFAULT_FILE_NAME = 'tactics-board.png';

interface SvgDimensions {
  width: number;
  height: number;
}

const normaliseScale = (value: number | undefined): number => {
  if (!value || Number.isNaN(value) || value <= 0) {
    return DEFAULT_SCALE;
  }

  return value;
};

const getSvgDimensions = (svg: SVGSVGElement): SvgDimensions => {
  const viewBox = svg.viewBox?.baseVal;

  if (viewBox && viewBox.width > 0 && viewBox.height > 0) {
    return {
      width: viewBox.width,
      height: viewBox.height,
    };
  }

  const widthAttr = Number(svg.getAttribute('width'));
  const heightAttr = Number(svg.getAttribute('height'));

  if (
    Number.isFinite(widthAttr) &&
    widthAttr > 0 &&
    Number.isFinite(heightAttr) &&
    heightAttr > 0
  ) {
    return {
      width: widthAttr,
      height: heightAttr,
    };
  }

  return {
    width: PITCH_VIEWBOX_WIDTH,
    height: PITCH_VIEWBOX_HEIGHT,
  };
};

const cloneSvgForExport = (
  sourceSvg: SVGSVGElement,
  width: number,
  height: number
): SVGSVGElement => {
  const clonedSvg = sourceSvg.cloneNode(true) as SVGSVGElement;

  clonedSvg.setAttribute('xmlns', SVG_NAMESPACE);
  clonedSvg.setAttribute('xmlns:xlink', SVG_XLINK_NAMESPACE);
  clonedSvg.setAttribute('width', String(width));
  clonedSvg.setAttribute('height', String(height));
  clonedSvg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  clonedSvg.style.background = 'transparent';
  clonedSvg.style.maxWidth = 'none';
  clonedSvg.style.height = 'auto';
  clonedSvg.style.borderRadius = '0';

  return clonedSvg;
};

const serialiseSvg = (svg: SVGSVGElement): string => {
  const serialised = new XMLSerializer().serializeToString(svg);

  if (serialised.startsWith('<?xml')) {
    return serialised;
  }

  return `<?xml version="1.0" encoding="UTF-8"?>${serialised}`;
};

const loadImage = (src: string): Promise<HTMLImageElement> =>
  new Promise((resolve, reject) => {
    const image = new Image();

    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error('Failed to load board export image.'));
    image.src = src;
  });

const canvasToBlob = (canvas: HTMLCanvasElement): Promise<Blob> =>
  new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) {
        reject(new Error('Failed to generate PNG file.'));
        return;
      }

      resolve(blob);
    }, 'image/png');
  });

const downloadBlob = (blob: Blob, fileName: string) => {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = objectUrl;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();

  URL.revokeObjectURL(objectUrl);
};

const paintPitchBackground = (
  context: CanvasRenderingContext2D,
  width: number,
  height: number
) => {
  const gradient = context.createLinearGradient(0, 0, 0, height);
  gradient.addColorStop(0, '#1f7a3d');
  gradient.addColorStop(0.5, '#1d6f38');
  gradient.addColorStop(1, '#1b6633');

  context.fillStyle = gradient;
  context.fillRect(0, 0, width, height);
};

export const exportBoardPng = async (
  svgElement: SVGSVGElement,
  options: ExportBoardPngOptions = {}
): Promise<void> => {
  if (!svgElement) {
    throw new Error('No pitch SVG found for export.');
  }

  const { width, height } = getSvgDimensions(svgElement);
  const scale = normaliseScale(options.scale);
  const fileName = options.fileName?.trim() || DEFAULT_FILE_NAME;

  const clonedSvg = cloneSvgForExport(svgElement, width, height);
  const serialisedSvg = serialiseSvg(clonedSvg);
  const svgBlob = new Blob([serialisedSvg], {
    type: 'image/svg+xml;charset=utf-8',
  });
  const svgObjectUrl = URL.createObjectURL(svgBlob);

  try {
    const image = await loadImage(svgObjectUrl);

    const canvas = document.createElement('canvas');
    canvas.width = Math.round(width * scale);
    canvas.height = Math.round(height * scale);

    const context = canvas.getContext('2d');
    if (!context) {
      throw new Error('PNG export is not available in this browser.');
    }

    context.setTransform(scale, 0, 0, scale, 0, 0);
    paintPitchBackground(context, width, height);
    context.drawImage(image, 0, 0, width, height);

    const pngBlob = await canvasToBlob(canvas);
    downloadBlob(pngBlob, fileName);
  } finally {
    URL.revokeObjectURL(svgObjectUrl);
  }
};

export default exportBoardPng;