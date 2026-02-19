import RiskCard from '../../components/RiskCard';
import type { RiskCardData } from '../../types';

export default function StampedeRiskCard({ data }: { data: RiskCardData }) {
    return <RiskCard data={{ ...data, title: 'Stampede Risk' }} />;
}

export function ChokePointCard({ data }: { data: RiskCardData }) {
    return <RiskCard data={{ ...data, title: 'Choke Point Analysis' }} />;
}

export function FlowCollisionCard({ data }: { data: RiskCardData }) {
    return <RiskCard data={{ ...data, title: 'Flow Collision' }} />;
}

export function BehaviourAnomalyCard({ data }: { data: RiskCardData }) {
    return <RiskCard data={{ ...data, title: 'Behaviour Anomaly' }} />;
}

export function QueueAnalysisCard({ data }: { data: RiskCardData }) {
    return <RiskCard data={{ ...data, title: 'Queue Analysis' }} />;
}
