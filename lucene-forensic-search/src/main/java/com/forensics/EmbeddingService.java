package com.forensics;

import ai.djl.huggingface.tokenizers.HuggingFaceTokenizer;
import ai.djl.huggingface.tokenizers.Encoding;
import ai.onnxruntime.*;

import java.nio.LongBuffer;
import java.util.Collections;

import java.nio.file.Paths;


public class EmbeddingService {
    private OrtEnvironment env;
    private OrtSession session;
    private HuggingFaceTokenizer tokenizer;

    public EmbeddingService(String onnxModelPath, String tokenizerPath) throws Exception {
        env = OrtEnvironment.getEnvironment();
        session = env.createSession(onnxModelPath, new OrtSession.SessionOptions());
        tokenizer = HuggingFaceTokenizer.newInstance(Paths.get(tokenizerPath));
    }

    public float[] embed(String text) throws Exception {
        Encoding encoding = tokenizer.encode(text);
        long[] inputIds = encoding.getIds();
        long[] attentionMask = encoding.getAttentionMask();
        long[] tokenTypeIds = new long[inputIds.length]; // all zeros by default in Java

        long[] shape = {1, inputIds.length};

        OnnxTensor inputIdsTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(inputIds), shape);
        OnnxTensor attentionMaskTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(attentionMask), shape);
        OnnxTensor tokenTypeIdsTensor = OnnxTensor.createTensor(env, LongBuffer.wrap(tokenTypeIds), shape);

        var inputs = new java.util.HashMap<String, OnnxTensor>();
        inputs.put("input_ids", inputIdsTensor);
        inputs.put("attention_mask", attentionMaskTensor);
        inputs.put("token_type_ids", tokenTypeIdsTensor);

        try (OrtSession.Result result = session.run(inputs)) {
            float[][][] output = (float[][][]) result.get(0).getValue();

            int seqLen = output[0].length;
            int dim = output[0][0].length;
            float[] pooled = new float[dim];
            int validTokens = 0;

            for (int i = 0; i < seqLen; i++) {
                if (attentionMask[i] == 1) {
                    for (int j = 0; j < dim; j++) {
                        pooled[j] += output[0][i][j];
                    }
                    validTokens++;
                }
            }
            for (int j = 0; j < dim; j++) {
                pooled[j] /= validTokens;
            }

            float norm = 0;
            for (float v : pooled) norm += v * v;
            norm = (float) Math.sqrt(norm);
            for (int j = 0; j < dim; j++) pooled[j] /= norm;

            return pooled;
    }
}
}