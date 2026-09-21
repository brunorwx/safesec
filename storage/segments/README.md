# Recording segments

`SegmentRecorder` accepts already-encoded bytes and writes finalized media plus JSON metadata sidecars. Camera codecs remain outside this package. Finalization replaces a temporary file atomically before publishing metadata, so interrupted writes do not appear as complete segments.
