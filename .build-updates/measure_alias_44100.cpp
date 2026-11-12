// 44.1kHz spectral measurements of the SAME measured TGFastZenerLimiter
// class and JUCE FIR oversampler used by the shipping plugin.
// Not a tanh proxy. Standalone harness to avoid DAW host dependencies.
#include <juce_dsp/juce_dsp.h>
#include "../Source/TGFastZenerLimiter.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <vector>
#include <set>
#include <string>
#include <stdexcept>

constexpr double SR=44100.0, PI=3.14159265358979323846264338;
constexpr int N=44100, ANALYZE=22050, BLOCK=256;

struct Result {
    double fund=0, aliasRMS=0, wantedRMS=0, outputRMS=0, gr=0;
    double aliasWorst=0, aliasWorstHz=0;
    double aliasAtThird=0, absThirdHz=0, passDb=0;
    int aliasCount=0;
};
double magAt(const std::vector<float>& s,double f) {
    // Exact coherent projection over the last 0.5sec, 2Hz FFT-bin spacing.
    // Tested frequencies and their aliases are integer-Hz/2-Hz bin aligned.
    if(f<0.5 || f>=SR*.5-0.5)return 0.0;
    const double phase=2*PI*f/SR;
    const double co=std::cos(phase),si=std::sin(phase);
    double cr=1.,ci=0.,a=0.,b=0.;
    const int first=N-ANALYZE;
    for(int j=0;j<ANALYZE;++j) {
        const double v=s[static_cast<size_t>(first+j)];
        a+=v*cr; b+=v*ci;
        const double nr=cr*co-ci*si;
        ci=ci*co+cr*si;cr=nr;
        if ((j & 4095)==4095) { const double r=1.0/std::hypot(cr,ci);cr*=r;ci*=r; }
    }
    return 2.0*std::hypot(a,b)/ANALYZE;
}
double fold(double f) {
    const double remainder=std::fmod(f,SR);
    return std::min(remainder,SR-remainder);
}
Result measure(const char* path,int factor,int pct,bool nonlinear,bool fixed,int f,int attack=1) {
    auto cell=std::make_unique<tgfast::TGFastZenerLimiter>();
    cell->loadReference(path);
    cell->prepare(SR*factor,static_cast<unsigned>(factor));
    tgfast::Controls controls{};
    controls.inputPct=pct;
    controls.outputPct=50; // unity output
    controls.attackMode=attack;
    controls.recovery=1;
    controls.softKnee=false;
    controls.nonlinear=nonlinear;
    cell->setControls(controls);
    if(fixed)cell->setReferenceToneForValidation(f);
    std::vector<float> y(N);
    constexpr double signalDb=-30., amplitude=std::pow(10.,signalDb/20.);
    std::unique_ptr<juce::dsp::Oversampling<float>> os;
    if(factor==4) {
        os=std::make_unique<juce::dsp::Oversampling<float>>(
            1,2,juce::dsp::Oversampling<float>::filterHalfBandFIREquiripple,true,true);
        os->initProcessing(BLOCK);
    }
    juce::AudioBuffer<float> buf(1,BLOCK);
    for(int start=0;start<N;start+=BLOCK) {
        const int n=std::min(BLOCK,N-start);
        for(int i=0;i<n;++i) {
            const double p=2.*PI*f*(start+i)/SR;
            buf.setSample(0,i,static_cast<float>(amplitude*std::sin(p)));
        }
        if(factor==1) {
            for(int i=0;i<n;++i)buf.setSample(0,i,
                static_cast<float>(cell->process(buf.getSample(0,i))));
        } else {
            auto chunk=juce::dsp::AudioBlock<float>(buf).getSubBlock(0,static_cast<size_t>(n));
            const juce::dsp::AudioBlock<const float> in(chunk);
            auto high=os->processSamplesUp(in);
            auto *p=high.getChannelPointer(0);
            for(size_t i=0;i<high.getNumSamples();++i)
                p[i]=static_cast<float>(cell->process(p[i]));
            os->processSamplesDown(chunk);
        }
        for(int i=0;i<n;++i)y[static_cast<size_t>(start+i)]=buf.getSample(0,i);
    }
    Result r;
    r.fund=magAt(y,f);
    r.gr=cell->currentGR();
    for(int i=N-ANALYZE;i<N;++i)
        r.outputRMS+=y[static_cast<size_t>(i)]*double(y[static_cast<size_t>(i)]);
    r.outputRMS=std::sqrt(r.outputRMS/ANALYZE);
    std::set<int> seen;
    const int maxH=20; // model's explicit K2-K20 output
    for(int h=2;h<=maxH;++h) {
        const double raw=double(h)*f, fq=fold(raw);
        if(fq<=0.0 || fq>=SR*.5 || std::abs(fq-f)<1.) continue;
        const int idx=int(std::round(fq*0.5)); // align 2-Hz frequency bins
        if(!seen.insert(idx).second)continue;
        const double level=magAt(y,fq);
        const bool wanted=raw<SR*.5;
        if(wanted)r.wantedRMS+=level*level;
        else {
            r.aliasRMS+=level*level;
            ++r.aliasCount;
            if(level>r.aliasWorst){r.aliasWorst=level;r.aliasWorstHz=fq;}
        }
        if(h==3){r.aliasAtThird=level;r.absThirdHz=fq;}
    }
    r.aliasRMS=std::sqrt(r.aliasRMS);
    r.wantedRMS=std::sqrt(r.wantedRMS);
    return r;
}
double toDb(double v) {return 20.*std::log10(std::max(1e-16,v));}
int main(int argc,char** argv) {
    if(argc<2) return 2;
    std::puts("mode,frequency_hz,input_pct,thd_on,tracker,fundamental_dbfs,GR_db,alias_rss_dBc,alias_worst_dBc,alias_worst_hz,alias_3rd_dBc,third_fold_hz,inband_harmonics_rss_dBc,output_rms_dbfs");
    for(bool fixed: {false,true}) {
        for(int f: {100,1000,5000,9000,10000,12000,15000,18000}) {
            for(int pct: {50,100}) {
                for(bool on:{false,true}) {
                    const auto x=measure(argv[1],1,pct,on,fixed,f);
                    const auto y=measure(argv[1],4,pct,on,fixed,f);
                    for(int mode:{1,4}) {
                        const auto& z=mode==1?x:y;
                        const auto ratio=[&](double a){return toDb(a/std::max(1e-15,z.fund));};
                        std::printf("%dx,%d,%d,%d,%s,%.3f,%.3f,%.3f,%.3f,%.0f,%.3f,%.0f,%.3f,%.3f\n",
                            mode,f,pct,on?1:0,fixed?"fixed":"live",
                            toDb(z.fund),z.gr,ratio(z.aliasRMS),ratio(z.aliasWorst),
                            z.aliasWorstHz,ratio(z.aliasAtThird),z.absThirdHz,
                            ratio(z.wantedRMS),toDb(z.outputRMS));
                    }
                    if(on && pct==100 && (f==9000||f==12000||f==15000))
                        std::fprintf(stderr,"CHECK %s %dHz: 1x alias %.1f dBc, 4x alias %.1f dBc; 1x GR %.1f, 4x GR %.1f\n",
                            fixed?"fixed":"live",f,
                            toDb(x.aliasRMS/std::max(1e-15,x.fund)),
                            toDb(y.aliasRMS/std::max(1e-15,y.fund)),
                            x.gr,y.gr);
                }
            }
        }
    }
    return 0;
}