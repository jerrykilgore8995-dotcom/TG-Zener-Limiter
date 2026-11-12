"""Apply fixed 4x linear-phase FIR oversampling after the v1.2 attack update.
All realtime allocations/filter design happen in prepareToPlay; no UI/parameter changes.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def change(rel, before, after):
    path=ROOT/rel
    s=path.read_text(encoding='utf-8')
    if s.count(before)!=1:
        raise RuntimeError(f'Expected one anchor in {rel}, found {s.count(before)}: {before[:90]!r}')
    path.write_text(s.replace(before,after,1),encoding='utf-8')

def replace_span(rel, start, end, replacement):
    p=ROOT/rel
    s=p.read_text(encoding='utf-8')
    a=s.index(start)
    b=s.index(end,a)
    p.write_text(s[:a]+replacement+'\n\n'+s[b:],encoding='utf-8')

# Keep the 13ms crest hold valid at 192kHz sessions with 4x processing (768kHz).
change('Source/TGFastZenerLimiter.h', 'std::array<Node,8192> nodes_{};', 'std::array<Node,16384> nodes_{};')
change('Source/TGFastZenerLimiter.h', 'if(window_>8191) throw std::invalid_argument("13ms hold requires larger ring for fs>630kHz"); reset();}', 'if(window_>16383) throw std::invalid_argument("13ms hold requires larger ring for fs>1.26MHz"); reset();}')
# All three ring index sites use the same power-of-two mask.
p=ROOT/'Source/TGFastZenerLimiter.h'
s=p.read_text(encoding='utf-8')
if s.count('&8191')!=3: raise RuntimeError('Unexpected crest ring indexing')
p.write_text(s.replace('&8191','&16383'),encoding='utf-8')
change('Source/TGFastZenerLimiter.h',
       'double hz_=1000.,fs_=44100., envelope_=0.;',
       'double hz_=1000.,fs_=44100., envelope_=0., follow_=0.001;')
change('Source/TGFastZenerLimiter.h',
       'void prepare(double fs){fs_=fs;coef_=std::exp(-1./(0.02*fs_));reset();}',
       'void prepare(double fs){fs_=fs;coef_=std::exp(-1./(0.02*fs_));\n'
       '        follow_=1.-std::pow(0.999,44100./fs_);reset();}')
change('Source/TGFastZenerLimiter.h',
       'hz_+=0.001*(autoHz-hz_);',
       'hz_+=follow_*(autoHz-hz_);')
change('Source/TGFastZenerLimiter.h',
       'void prepare(double sampleRate) {',
       'void prepare(double sampleRate, unsigned oversamplingFactor=1u) {')
change('Source/TGFastZenerLimiter.h',
       'fs_=clip(sampleRate,8000.,500000.);hold_.prepare(fs_);tone_.prepare(fs_);',
       'fs_=clip(sampleRate,8000.,1000000.);hold_.prepare(fs_);tone_.prepare(fs_);\n'
       '        harmonicMask_=32u*std::clamp(oversamplingFactor,1u,8u)-1u;')
change('Source/TGFastZenerLimiter.h',
       'if((samples_++ & 31u)==0u){',
       'if((samples_++ & harmonicMask_)==0u){')
change('Source/TGFastZenerLimiter.h',
       'int testBias_=-1;uint64_t samples_=0;',
       'int testBias_=-1;uint64_t samples_=0;uint64_t harmonicMask_=31u;')

# Wrap actual compressor + harmonic generation at 4x, using JUCE's high-quality
# FIR half-band up/downsampling. Input/output filtering belongs outside the cell.
change('Source/PluginProcessor.h',
       '#include <juce_audio_processors/juce_audio_processors.h>',
       '#include <juce_audio_processors/juce_audio_processors.h>\n'
       '#include <juce_dsp/juce_dsp.h>')
change('Source/PluginProcessor.h',
       'void releaseResources() override;',
       'void releaseResources() override;\n    void reset() override;')
change('Source/PluginProcessor.h',
       '    double wet = 1.0;',
       '    std::unique_ptr<juce::dsp::Oversampling<float>> oversampler;\n'
       '    juce::AudioBuffer<float> dryDelay, dryScratch;\n'
       '    int latencySamples = 0, dryWrite = 0, maxPreparedBlock = 1;\n'
       '    double wet = 1.0;')

prepare=r'''void TGZenerRackAudioProcessor::prepareToPlay(double sampleRate, int maximumExpectedSamplesPerBlock)
{
    wetSmoothing = 1.0 - std::exp(-1.0 / (sampleRate * 0.005));
    wet = parameters.getRawParameterValue("active")->load() > 0.5f ? 1.0 : 0.0;
    grLeft.store(0.0f); grRight.store(0.0f);
    setLatencySamples(0);
    oversampler.reset();
    dryWrite = latencySamples = 0;
    if (!hasReference) return;

    constexpr unsigned oversamplingFactor = 4;
    maxPreparedBlock = juce::jmax(1, maximumExpectedSamplesPerBlock);
    const int channels = juce::jlimit(1, 2, getTotalNumInputChannels());
    // Two FIR half-band stages, linear phase; integer latency for host PDC.
    oversampler = std::make_unique<juce::dsp::Oversampling<float>>(
        static_cast<size_t>(channels), 2,
        juce::dsp::Oversampling<float>::filterHalfBandFIREquiripple, true, true);
    oversampler->initProcessing(static_cast<size_t>(maxPreparedBlock));
    latencySamples = juce::jmax(0, juce::roundToInt(oversampler->getLatencyInSamples()));
    dryDelay.setSize(channels, juce::jmax(1, latencySamples));
    dryDelay.clear();
    dryScratch.setSize(channels, maxPreparedBlock);
    dryScratch.clear();
    setLatencySamples(latencySamples);

    // Attack/recovery/13ms hold are defined in milliseconds, not sample counts.
    left->prepare(sampleRate * oversamplingFactor, oversamplingFactor);
    right->prepare(sampleRate * oversamplingFactor, oversamplingFactor);
}

void TGZenerRackAudioProcessor::releaseResources()
{
    oversampler.reset();
}

void TGZenerRackAudioProcessor::reset()
{
    if (oversampler) oversampler->reset();
    dryDelay.clear();
    dryScratch.clear();
    dryWrite=0;
    if (hasReference) { left->reset(); right->reset(); }
}'''
replace_span('Source/PluginProcessor.cpp',
             'void TGZenerRackAudioProcessor::prepareToPlay(',
             'void TGZenerRackAudioProcessor::processBlock(',prepare)

process=r'''void TGZenerRackAudioProcessor::processBlock(juce::AudioBuffer<float>& buffer,
                                             juce::MidiBuffer& midi)
{
    juce::ignoreUnused(midi);
    juce::ScopedNoDenormals noDenormals;
    if (!hasReference || !oversampler || buffer.getNumSamples()==0) return;

    tgfast::Controls c;
    c.inputPct = static_cast<int>(std::lround(parameters.getRawParameterValue("input")->load()));
    c.outputPct = static_cast<int>(std::lround(parameters.getRawParameterValue("output")->load()));
    c.recovery = static_cast<int>(std::lround(parameters.getRawParameterValue("recovery")->load()));
    c.attackMode = juce::jlimit(0, 2, static_cast<int>(std::lround(
                       parameters.getRawParameterValue("attack")->load())));
    c.softKnee = parameters.getRawParameterValue("softKnee")->load() > 0.5f;
    c.nonlinear = parameters.getRawParameterValue("cell")->load() > 0.5f;
    const double wetTarget = parameters.getRawParameterValue("active")->load() > 0.5f ? 1.0 : 0.0;
    left->setControls(c);
    right->setControls(c);

    const int channels=juce::jmin(2, buffer.getNumChannels());
    auto host=juce::dsp::AudioBlock<float>(buffer);
    for (int offset=0;offset<buffer.getNumSamples();offset+=maxPreparedBlock)
    {
        const int n=juce::jmin(maxPreparedBlock, buffer.getNumSamples()-offset);
        auto chunk=host.getSubBlock(static_cast<size_t>(offset),static_cast<size_t>(n));

        // Preserve a *latency aligned* dry signal for smooth IN bypass.
        // This avoids phase combing between undelayed dry and FIR-delayed wet.
        for(int i=0;i<n;++i)
        {
            for(int ch=0;ch<channels;++ch)
            {
                const float x=chunk.getSample(static_cast<size_t>(ch),static_cast<size_t>(i));
                float dry=x;
                if(latencySamples>0)
                {
                    dry=dryDelay.getSample(ch,dryWrite);
                    dryDelay.setSample(ch,dryWrite,x);
                }
                dryScratch.setSample(ch,i,dry);
            }
            if(latencySamples>0 && ++dryWrite>=latencySamples) dryWrite=0;
        }

        const juce::dsp::AudioBlock<const float> inputBlock(chunk);
        auto high=oversampler->processSamplesUp(inputBlock);
        auto* l=high.getChannelPointer(0);
        auto* r=channels==2?high.getChannelPointer(1):nullptr;
        for(size_t i=0;i<high.getNumSamples();++i)
        {
            l[i]=static_cast<float>(left->process(l[i]));
            if(r!=nullptr) r[i]=static_cast<float>(right->process(r[i]));
        }
        // FIR lowpass suppresses out-of-band distortion *before decimation*.
        oversampler->processSamplesDown(chunk);
        for(int i=0;i<n;++i)
        {
            wet += wetSmoothing*(wetTarget-wet);
            for(int ch=0;ch<channels;++ch)
            {
                const auto dry=dryScratch.getSample(ch,i);
                const auto processed=chunk.getSample(static_cast<size_t>(ch),static_cast<size_t>(i));
                chunk.setSample(static_cast<size_t>(ch),static_cast<size_t>(i),
                    dry+static_cast<float>(wet)*(processed-dry));
            }
        }
    }
    grLeft.store(wetTarget > 0.5 ? static_cast<float>(left->currentGR()) : 0.0f,
                 std::memory_order_relaxed);
    grRight.store(wetTarget > 0.5 && channels == 2
                  ? static_cast<float>(right->currentGR()) : 0.0f,
                  std::memory_order_relaxed);
}'''
replace_span('Source/PluginProcessor.cpp',
             'void TGZenerRackAudioProcessor::processBlock(',
             'void TGZenerRackAudioProcessor::getStateInformation(',process)

change('CMakeLists.txt','VERSION 1.2.0','VERSION 1.3.0')
change('CMakeLists.txt','    juce::juce_audio_utils\n',
                         '    juce::juce_audio_utils\n    juce::juce_dsp\n')

# Regression test for a worst-case high-frequency odd-harmonic waveshaper:
# 9kHz at 44.1kHz -> folded 3rd at 17.1kHz without oversampling.
test=r'''#include <juce_dsp/juce_dsp.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <stdexcept>
#include <vector>
static constexpr double pi=3.14159265358979323846;
static double foldAmplitude(const std::vector<float>& x, double hz, double fs)
{
    const int n=44100, start=static_cast<int>(x.size())-n;
    double re=0, im=0;
    for(int i=0;i<n;++i) {
        const double a=2*pi*hz*i/fs, s=x[static_cast<size_t>(start+i)];
        re+=s*std::cos(a); im+=s*std::sin(a);
    }
    return 2.*std::hypot(re,im)/n;
}
int main()
{
    constexpr int sr=44100, blocksize=128, count=88200;
    constexpr double inputHz=9000.0, aliasHz=17100.0;
    juce::dsp::Oversampling<float> os(1,2,
        juce::dsp::Oversampling<float>::filterHalfBandFIREquiripple,true,true);
    os.initProcessing(blocksize);
    juce::AudioBuffer<float> block(1,blocksize);
    std::vector<float> direct(count),filtered(count);
    for(int offset=0;offset<count;offset+=blocksize) {
        const int n=std::min(blocksize,count-offset);
        for(int i=0;i<n;++i) {
            const float x=0.7f*static_cast<float>(std::sin(2*pi*inputHz*(offset+i)/sr));
            block.setSample(0,i,x);
            direct[static_cast<size_t>(offset+i)]=std::tanh(3.f*x);
        }
        auto base=juce::dsp::AudioBlock<float>(block).getSubBlock(0,static_cast<size_t>(n));
        const juce::dsp::AudioBlock<const float> input(base);
        auto up=os.processSamplesUp(input);
        float* high=up.getChannelPointer(0);
        for(size_t i=0;i<up.getNumSamples();++i) high[i]=std::tanh(3.f*high[i]);
        os.processSamplesDown(base);
        for(int i=0;i<n;++i) filtered[static_cast<size_t>(offset+i)]=block.getSample(0,i);
    }
    const double before=foldAmplitude(direct,aliasHz,sr);
    const double after=foldAmplitude(filtered,aliasHz,sr);
    const double reduction=20*std::log10(before/std::max(1e-12,after));
    const double passBefore=foldAmplitude(direct,inputHz,sr);
    const double passAfter=foldAmplitude(filtered,inputHz,sr);
    const double passDiff=20*std::log10(passAfter/passBefore);
    std::printf("44.1kHz / 4x FIR: folded 9kHz 3rd at 17.1kHz: %.1f dB reduction; fundamental delta %.2f dB; latency %.1f samples\n",
                reduction,passDiff,os.getLatencyInSamples());
    if (!(reduction>18.0 && std::abs(passDiff)<1.0))
        throw std::runtime_error("4x FIR anti-alias or passband response outside acceptance");
    return 0;
}'''
(ROOT/'tests/test_oversampling.cpp').write_text(test,encoding='utf-8')
with (ROOT/'CMakeLists.txt').open('a',encoding='utf-8') as f:
    f.write('''
add_executable(tg_test_oversampling tests/test_oversampling.cpp)
target_link_libraries(tg_test_oversampling PRIVATE juce::juce_dsp juce::juce_recommended_config_flags)
add_test(NAME tg_oversampling COMMAND tg_test_oversampling)
''')
print('Applied fixed 4x FIR oversampling, latency-aligned dry path, exact ms timing, and alias regression test.')
