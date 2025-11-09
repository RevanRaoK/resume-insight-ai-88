import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowRight, FileText, Brain, Target } from "lucide-react";
import { useNavigate } from "react-router-dom";

const Index = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-6">
            SmartResume AI
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
            Transform your resume with AI-powered analysis and career guidance. Get intelligent feedback, optimize your content, and land your dream job faster.
          </p>
        </div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <FileText className="h-8 w-8 text-blue-600 mb-2" />
              <CardTitle>Smart Document Processing</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Upload your resume in PDF, DOCX, or TXT format. Our AI automatically extracts and analyzes your content with advanced natural language processing.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <Brain className="h-8 w-8 text-green-600 mb-2" />
              <CardTitle>AI-Powered Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Get comprehensive feedback on your resume's strengths and weaknesses. Our AI identifies areas for improvement and provides actionable suggestions.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <Target className="h-8 w-8 text-purple-600 mb-2" />
              <CardTitle>Career Guidance</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Receive personalized recommendations based on your career goals and industry standards. Optimize your resume for specific job positions and companies.
              </CardDescription>
            </CardContent>
          </Card>
        </div>

        {/* CTA Section */}
        <div className="text-center">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 max-w-2xl mx-auto">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
              Ready to Optimize Your Resume?
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-6">
              Join thousands of professionals who have improved their resumes with our AI-powered analysis tool.
            </p>
            <Button 
              size="lg" 
              className="bg-blue-600 hover:bg-blue-700 text-white"
              onClick={() => navigate('/auth')}
            >
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Index;
