import { GetStartedButton } from "../Buttons/GetStartedButton";
import { HeroImage } from "./HeroImage";
import { PrimaryHeader } from "./PrimaryHeader";
import { SecondaryHeader } from "./SecondaryHeader";
import "./css/HeroSection.css";

interface HeroSectionProps {
  onGetStarted?: () => void;
}

export const HeroSection = ({ onGetStarted }: HeroSectionProps) => {
  return (
    <div className="heroSection">
      <div className="heroSectionLeft">
        <PrimaryHeader />
        <SecondaryHeader />
        <GetStartedButton onClick={onGetStarted} />
      </div>
      <div className="heroSectionRight">
        <HeroImage/>
      </div>
    </div>
  );
};
