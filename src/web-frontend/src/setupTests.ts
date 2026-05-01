import '@testing-library/jest-dom';

class MockDOMMatrix {
    constructor(_init?: string | number[]) { }

    a = 1;
    b = 0;
    c = 0;
    d = 1;
    e = 0;
    f = 0;

    multiplySelf() {
        return this;
    }

    preMultiplySelf() {
        return this;
    }

    translateSelf() {
        return this;
    }

    scaleSelf() {
        return this;
    }

    rotateSelf() {
        return this;
    }

    invertSelf() {
        return this;
    }

    static fromFloat32Array(_array32: Float32Array) {
        return new MockDOMMatrix();
    }

    static fromFloat64Array(_array64: Float64Array) {
        return new MockDOMMatrix();
    }

    static fromMatrix(_other?: DOMMatrixInit) {
        return new MockDOMMatrix();
    }
}

const domMatrixMock = MockDOMMatrix as unknown as typeof DOMMatrix;

if (typeof globalThis.DOMMatrix === 'undefined') {
    (globalThis as typeof globalThis & { DOMMatrix: typeof DOMMatrix }).DOMMatrix =
        domMatrixMock;
}

if (typeof window !== 'undefined' && typeof window.DOMMatrix === 'undefined') {
    (window as Window & typeof globalThis & { DOMMatrix: typeof DOMMatrix }).DOMMatrix =
        domMatrixMock;
}
